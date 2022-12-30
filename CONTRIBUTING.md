# Contribution
If you wish to contribute to `DJ Tools`, please follow these development rules:
1. All development branches must be made off of the appropriate release branch (e.g. `releases/2.4.0` or `releases/2.3.1`)
2. Development branches must have a concise name for the feature or bugfix specifically targeted by that branch (e.g. `xml-track-randomization` or `improve-spotify-stability`)
3. PRs should be made from development branches prefixed with your GitHub username (e.g. `a-rich/improve-spotify-stability`)
4. New features are added to the next minor version (`2.x.0`) which will be released quarterly
5. Bug fixes are added to the next patch version (`2.3.x`) which will be released as needed
6. All development branchs should originate from and be linked to an associated Issue
7. All `push` and `pull_request` events trigger a `pytest-cov` Action; only runs passing with 100% coverage can be merged