# System Overview

`djtools` is a set of packages which, together, provide functional interfaces to streamline a multitude collection curation tasks.

Although there are parts of `djtools`, like the collection package, that are designed to [operate interactively](./collections_api.md), `djtools` is primarily intended to be used as a CLI.

When executed, the [main function](https://github.com/a-rich/DJ-Tools/blob/main/djtools/__init__.py) of `djtools` builds 
a configuration, iterates through the top-level operations exposed by each package, and executes those operations as determined by the configuration.

When building the configuration, `djtools` first looks for a [config.yaml](https://github.com/a-rich/DJ-Tools/blob/main/djtools/configs/config.yaml) in the configs folder from which to load the configuration objects.
If no config file is found, default values defined in the Pydantic models are used.
If CLI arguments are provided, they override the corresponding configuration options.

The top-level operation exposed by the different `djtools` packages all accept a `BaseConfig` object which is returned from the `build_config` function.
In short, the `BaseConfig` defines some options common to all packages and has all the package-specific `Config` objects merged into it.
