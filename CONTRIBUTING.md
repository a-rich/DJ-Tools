# Contribution
If you wish to contribute to DJ Tools, please follow these development rules:
1. Development branches must originate from and be linked to an associated Issue
1. Development branches should be made off of the appropriate release branch (e.g. `releases/2.4.0`) to minimize conflicts
1. Development branches must have a concise name for the feature or bugfix specifically targeted by that branch (e.g. `xml-track-randomization` or `improve-spotify-stability`)
1. Commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org/) standard
1. Commit messages must include a `Why?` and `What?` section in the body describing the reason for and specifics of the commit
1. Commits must pass all tests with 100% code coverage; `push` and `pull_request` events trigger a [pytest-cov](https://github.com/a-rich/DJ-Tools/actions/workflows/test.yaml) Action