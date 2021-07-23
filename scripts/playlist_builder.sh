#!/bin/zsh
source /Users/aweeeezy/.zshrc
cd /Users/aweeeezy/Work/Repos/DJ_tools/scripts
echo "$(date)" >> playlist_builder.log
pyenv activate lrm-vision
python playlist_builder.py --subreddit darkstep >> playlist_builder.log
python playlist_builder.py --subreddit realdubstep >> playlist_builder.log
python playlist_builder.py --subreddit futurebeats >> playlist_builder.log
python playlist_builder.py --subreddit HalftimeDnB >> playlist_builder.log
python playlist_builder.py --subreddit neurofunk >> playlist_builder.log
python playlist_builder.py --subreddit spacebass >> playlist_builder.log
python playlist_builder.py --subreddit trap >> playlist_builder.log
python playlist_builder.py --subreddit wonky >> playlist_builder.log
echo -e "\n\n"
