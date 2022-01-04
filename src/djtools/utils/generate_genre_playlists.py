"""This module is used to automatically generate a playlist structure using
the ID3 genre tags of tracks. This is done by:
    * parsing a Rekordbox XML file to extract tracks and splitting their genre
            tags on a delimiter
    * parsing 'generate_genre_playlists.json' to infer the desired genre
            playlist structure
    * inserting tracks into the playlist structure using their genre tag(s)

The 'generate_genre_playlists.json' structure supports playlists and folders of
playlists with as many layers of nesting as desired. Each folder level (except
the root level) will generate an 'All <folder name>' playlist which will
aggregate tracks added to subplaylists / subfolders of that folder.

Tracks of genres which do not have a corresponding playlist in the JSON
structure will be inserted into either an 'Other' playlist or an 'Other' folder
with individual genre subplaylists (depending on
'GENERATE_GENRE_PLAYLISTS_REMAINDER')...

Specific genres can be ignored from this 'Other' playlist / folder generation
process by specifying them as a folder called '_ignore' in
'generate_genre_playlists.json'.

NOTE: if you have playlists with non-unique names, tracks with matching genre
tags will be inserted into all of those playlists...the exception to this is
for playlists named 'Hip Hop' that exist at the top-level versus any sub-level
(see docstring of 'add_tracks' function for more detail).

NOTE: there is special logic for creating an additional grouping of tracks that
have genre tags that all include the substring 'techno'...the purpose of this
is to support the automatic generation of a 'Pure Techno' playlist despite
there being no such genre tag in my personal beatcloud (see docstring of
'get_track_genres' for more detail).
"""
import json
import logging
import os

from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


def generate_genre_playlists(config):
    """This function generates a playlist structure using
    'generate_genre_playlists.json' and the ID3 genre tags of tracks in a
    Collection.

    Args:
        config (dict): configuration object

    Raises:
        FileNotFoundError: 'XML_PATH' must exist
    """
    if not os.path.exists(config['XML_PATH']):
        raise FileNotFoundError(f'{config["XML_PATH"]} does not exist!')

    soup = BeautifulSoup(open(config['XML_PATH'], encoding='utf-8').read(),
                         'xml')
    tracks = get_track_genres(soup, config['GENRE_TAG_DELIMITER'])
    genres = set()
    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           'configs', 'generate_genre_playlists.json'),
              encoding='utf-8') as _file:
        playlists = create_playlists(soup, json.load(_file), genres,
                                     top_level=True)

    if config['GENERATE_GENRE_PLAYLISTS_REMAINDER']:
        add_other(soup, config['GENERATE_GENRE_PLAYLISTS_REMAINDER'], genres,
                  tracks, playlists)

    add_tracks(soup, playlists, tracks)
    wrap_playlists(soup, playlists)

    _dir, _file = os.path.split(config['XML_PATH'])
    auto_xml_path = os.path.join(_dir, f'auto_{_file}')
    with open(auto_xml_path, mode='wb', encoding=soup.orignal_encoding) as \
            _file:
        _file.write(soup.prettify('utf-8'))


def get_track_genres(soup, delimiter):
    """Creates a map of genres to lists of tracks belonging to those genres.
    Supports multiple genres per track via a split on 'delimiter'.

    There is special logic regarding tracks which have genre tags that all
    contain the string 'techno'...since my desired playlist structure
    includes a 'Pure Techno' playlist, and there is no genre tag for
    'Pure Techno', tracks which meet the aforementioned rule are inserted into
    a list keyed by 'Pure Techno' to support the automatic generation of such a
    playlist.

    Args:
        soup (bs4.BeautifulSoup): parsed XML
        delimiter (str): character(s) used to deliminate genres in the genre
                         ID3 tag

    Returns:
        dict: map of genres to lists of (track_id, genres) tuples
    """
    tracks = {}
    for track in soup.find_all('TRACK'):
        if not track.get('Location'):
            continue
        track_genres = [x.strip() for x in track['Genre'].split(delimiter)]

        # NOTE: special logic to create 'Pure Techno' playlist despite there
        # being no 'Pure Techno' genre tag
        if all(('techno' in x.lower() for x in track_genres)):
            if 'Pure Techno' in tracks:
                tracks['Pure Techno'].append((track['TrackID'], track_genres))
            else:
                tracks['Pure Techno'] = [(track['TrackID'], track_genres)]

        for genre in track_genres:
            if genre in tracks:
                tracks[genre].append((track['TrackID'], track_genres))
            else:
                tracks[genre] = [(track['TrackID'], track_genres)]

    return tracks


def create_playlists(soup, content, genres, top_level=False):
    """Recursively traverses 'generate_genre_playlists.json' and creates the
    corresponding XML tag structure to be populated with tracks. If a folder is
    encountered, an additional playlist is created called 'All <folder name>'
    (this does not apply to the top-level folder). If a folder named '_ignore'
    is encountered, genre playlists specified in the associated 'playlists'
    list will not have a tag created for them, but the genres will be added to
    the 'genres' set so the corresponding tracks will be ignored when
    generating the 'Other' folder / playlist.

    Args:
        soup (bs4.BeautifulSoup): parsed XML
        content (str or dict): playlist name or folder name with playlists
        genres (set): playlist genres set to populate

    Raises:
        ValueError: 'generate_genre_playlists.json' must be properly formatted

    Returns:
        bs4.element.Tag: populated playlist structure
    """
    if isinstance(content, dict):
        content = {k.lower(): v for k, v in content.items()}
        if content['name'] == '_ignore':
            genres.update(set(content['playlists']))
        else:
            folder = soup.new_tag('NODE', Name=content['name'], Type="0")
            if not top_level:
                _all = soup.new_tag('NODE', KeyType="0",
                                    Name=f'All {content["name"]}', Type="1")
                folder.append(_all)
            for playlist in content['playlists']:
                _playlist = create_playlists(soup, playlist, genres)
                if _playlist:
                    folder.append(_playlist)
            return folder
    elif isinstance(content, str):
        genres.add(content)
        playlist = soup.new_tag('NODE', KeyType="0", Name=content, Type="1")
        return playlist
    else:
        raise ValueError('Encountered invalid input type ' \
                         f"{type(content)}: {content}")


def add_other(soup, remainder_type, genres, tracks, playlists):
    """Identifies the remainder genres by taking the set difference of all
    track genres with those that appear in 'generate_genre_playlists.json'. If
    'remainder_type' is 'playlist', then all these tracks are inserted into an
    'Other' playlist. If 'remainder_type' is 'folder', then an 'Other' folder
    is created and playlists for each genre are populated.

    Args:
        soup (bs4.BeautifulSoup): parsed XML
        remainder_type (str): whether to put genres not specified in
                              'generate_genre_playlists.json' into an 'Other'
                              folder with individual playlists for each genre
                              or into a single 'Other' playlist
        genres (set): all the genres in 'generate_genre_playlists.json'
        tracks (dict): map of genres to lists of (track_id, genres) tuples
        playlists (bs4.element.Tag): empty playlist structure
    """
    if remainder_type == 'folder':
        folder = soup.new_tag('NODE', Name='Other', Type='0')
        for other in sorted(set(tracks).difference(genres)):
            playlist = soup.new_tag('NODE', Name=other, Type="1", KeyType="0")
            folder.append(playlist)
        playlists.append(folder)
    elif remainder_type == 'playlist':
        playlist = soup.new_tag('NODE', Name='Other', Type="1", KeyType="0")
        playlists.append(playlist)
    else:
        logger.error(f'Invalid remainder type "{remainder_type}"')


def add_tracks(soup, playlists, tracks):
    """Iterates all the genre playlists in the playlist structure and inserts
    tracks having that genre tag into the playlist. Additionally recursively
    searches the parent of the 'playlist' node for a playlist called
    'All <playlist.parent>'. If that exists, the track is also inserted into
    this playlist...

    For example, the 'Bass' folder has an 'All Bass' playlist, and a folder
    called 'DnB' which contains both 'All DnB' and 'Techstep' playlists; any
    track inserted into 'Techstep' will also be inserted into 'All DnB' and
    'All Bass'.

    If any playlist has a non-unique name, then tracks with a matching genre
    tag will be inserted into all of those playlists. There is special logic
    regarding the 'Hip Hop' playlists. My desired genre playlist structure has
    a 'Hip Hop' playlist at the top-level which is meant to hold Hip Hop tracks
    that are traditional (i.e. pure Hip Hop / Rap). It also has a 'Hip Hop'
    playlist which resides in the 'Hip Hop Beats' folder under the 'Bass'
    folder; this playlist is meant to hold tracks in which Hip Hop is merely a
    component among other elements (like Space Bass, Trap, etc.). This function
    will only insert tracks into the former playlist if all the genre tags
    contain only 'R&B' and/or 'Hip Hop'. It will only insert tracks into the
    latter if at least one of the tags does NOT contain 'R&B' and 'Hip Hop'.

    Args:
        soup (bs4.BeautifulSoup): parsed XML
        playlists (bs4.element.Tag): empty playlist structure
        tracks (dict): map of genres to lists of (track_id, genres) tuples
    """
    seen = {}
    for playlist in playlists.find_all('NODE', {'Type': '1'}):
        seen_index = f"{playlist.parent['Name']} -> {playlist['Name']}"
        if seen_index not in seen:
            seen[seen_index] = set()

        # NOTE: special logic to distinguish between the general 'Hip Hop'
        # playlist (a.k.a. pure Hip Hop) and the 'Hip Hop' playlist under the
        # 'Bass' folder (a.k.a. bass Hip Hop)
        pure_hip_hop = bass_hip_hop = False
        if playlist['Name'] == 'Hip Hop':
            if playlist.parent['Name'] == 'Genres':
                pure_hip_hop = True
            else:
                bass_hip_hop = True

        for track_id, genres in tracks.get(playlist['Name'], []):
            # NOTE: special logic to distinguish between the general 'Hip Hop'
            # playlist (a.k.a. pure Hip Hop) and the 'Hip Hop' playlist under
            # the 'Bass' folder (a.k.a. bass Hip Hop)
            skip_add = False
            if pure_hip_hop and \
                    any(('r&b' not in x.lower() and 'hip hop' not in x.lower()
                         for x in genres)):
                skip_add = True
            if bass_hip_hop and \
                    all(('r&b' in x.lower() or 'hip hop' in x.lower()
                         for x in genres)):
                skip_add = True
            if skip_add:
                continue

            if track_id not in seen[seen_index]:
                playlist.append(soup.new_tag('TRACK', Key=track_id))
                seen[seen_index].add(track_id)

            parent = playlist.parent
            while parent:
                try:
                    _all = parent.find_all('NODE',
                                           {'Name': f'All {parent["Name"]}'},
                                           recursive=False)[0]
                    _seen_index = f"{_all.parent['Name']} -> {_all['Name']}"
                    if _seen_index not in seen:
                        seen[_seen_index] = set()

                    if track_id not in seen[_seen_index]:
                        _all.append(soup.new_tag('TRACK', Key=track_id))
                        seen[_seen_index].add(track_id)
                except IndexError:
                    break
                parent = parent.parent


def wrap_playlists(soup, playlists):
    """Creates a folder called 'AUTO_GENRES', inserts the generated playlist
    structure into it, and then inserts 'AUTO_GENRES' into the root of the
    'Playlist' folder.

    Args:
        soup (bs4.BeautifulSoup): parsed XML
        playlists (bs4.element.Tag): playlist structure
    """
    playlists_root = soup.find_all('NODE', {'Name': 'ROOT', 'Type': '0'})[0]
    new_playlist = soup.new_tag('NODE', Name='AUTO_GENRES', Type="0")
    new_playlist.insert(0, playlists)
    playlists_root.insert(0, new_playlist)
