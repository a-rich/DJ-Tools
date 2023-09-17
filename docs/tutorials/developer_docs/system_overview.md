# System Overview


## Contents
- [djtools as a CLI](#djtools-as-aclij)
- [djtools as a Library](#djtools-as-a-library)
- [CI](#ci)


## djtools as a CLI
`djtools` is a set of packages that provide functional interfaces to streamline tasks.

Although there are parts of `djtools`, like the collection package, that are designed to [operate interactively](./collections_api.md), `djtools` is primarily intended to be used as a CLI.

In a nutshell, the [main function](https://github.com/a-rich/DJ-Tools/blob/main/djtools/__init__.py) of `djtools` builds 
a configuration, iterates through the top-level operations exported by each package, and executes those operations as determined by the configuration.

When building the configuration, `djtools` first looks for a [config.yaml](https://github.com/a-rich/DJ-Tools/blob/main/djtools/configs/config.yaml) in the configs folder from which to load the configuration objects.
If no config file is found, default values defined in the Pydantic models are used.
If CLI arguments are provided, they override the corresponding configuration options:

::: djtools.configs.helpers.build_config
    options:
        show_docstring_description: false
        show_docstring_parameters: false
        show_docstring_raises: false
        show_docstring_returns: false

At the end of config building, a `BaseConfig` object containing the union of the package configs' options is returned.
The top-level operations exported by the different `djtools` packages all take a `BaseConfig` object as an argument.


## djtools as a Library
The `djtools` library is organized into 5 packages:

- `configs`
- `collection`
- `spotify`
- `sync`
- `utils`

Each of the packages `collection`, `spotify`, `sync`, and `utils` export the module functions that implement the top-level features of `djtools`.

Additionally, the `configs` package exports `build_config` which generates the `BaseConfig` object that must be passed into all of the other exported functions.

The exception are the `*Collection`, `*Playlist`, and `*Track` classes exported from the `collection` package.
These are exported as a convenience for interactive collection manipulation in a Python interpreter.

Note that, while `build_config` accepts an optional path to a `config.yaml`, features that interact with the other YAML configs (`collection_playlists.yaml` and `spotify_playlists.yaml`) still reference those config paths relative to the source.

## CI
There are several GitHub Actions bound to the lifecycle of `djtools`.

The [pytest-coverage](https://github.com/a-rich/DJ-Tools/blob/main/.github/workflows/pytest-coverage.yaml) and [pylint](https://github.com/a-rich/DJ-Tools/blob/main/.github/workflows/pylint.yaml) workflows are triggered on pull request events.
Passing both of these workflows is a check for merges into release branches or `main`.
A pass rate of 100% is required.

On pushes to `releases/**` branches, changes to `requirements.txt` or `.py` files trigger the [release-dev](https://github.com/a-rich/DJ-Tools/blob/main/.github/workflows/release-dev.yaml) workflow which performs a pre-release version bump and wheel release.
Changes to `.md` files trigger the [deploy-dev-docs](https://github.com/a-rich/DJ-Tools/blob/main/.github/workflows/deploy-dev-docs.yaml) workflow which copies files to a shadow repository and deploys docs on that repo's GitHub Pages.

On pushes to `main`, the [release-prod](https://github.com/a-rich/DJ-Tools/blob/main/.github/workflows/release-prod.yaml) and [deploy-prod-docs](https://github.com/a-rich/DJ-Tools/blob/main/.github/workflows/deploy-prod-docs.yaml) workflows are triggered which perform essentially the same steps as the equivalent dev workflows except the version is finalized instead of bumped and the docs are deployed on the main repository's GitHub Pages. 
