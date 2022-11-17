If you wish to contribute to `DJ Tools`, please follow these development rules:
1. Only release branches (`major: 3.0.0`, `minor: 2.1.0`, `patch: 2.0.5`) can be made off of `main`
2. The only commits to `main` that are allowed are updates to the `Release Plan` portion of this `README`; make a PR for this commit and, once approved, rebase the corresponding release branch on top of it
2. New features are added to the next minor release branch which will be created and released quarterly (the 1st of January, April, July, and October)
3. Bug fixes are added to the next patch release branch which will be created whenever the last is published to PyPI
3. Non-release branches must have a concise name for the feature or bugfix specifically targeted by that branch (e.g. `xml-track-randomization`)
4. All development work must be done on an unshared branch made off of the appropriate feature or bugfix branch (e.g. `alex_xml-track-randomization`)
5. All development branches must rebase their changes on top of the respective feature / bugfix branch before merging (squash, fixup, reword, etc. as needed to ensure a clean commit history)
6. Make a rebase PR when you are ready for the next beta release; I will rebase the feature / bugfix branch on top of the appropriate release branch and publish a beta release