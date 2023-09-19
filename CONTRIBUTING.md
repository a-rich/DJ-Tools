# Contribution
If you wish to contribute to DJ Tools, please follow these development rules:
1. Development branches must:
    1. be linked to an Issue
    1. branch from `releases/*`
    1. have a concise name for the feature or bugfix specifically targeted by that branch (e.g. `xml-track-randomization` or `improve-spotify-stability`)
1. Commit messages must:
    1. follow the [Conventional Commits](https://www.conventionalcommits.org/) standard
    1. include a `Why?` and `What?` section in the body describing the reason for and specifics of the commit
    1. include necessary updates to the [docs](https://github.com/a-rich/DJ-Tools/tree/main/docs)

## CI
On `pull_request` events, [pytest-coverage](https://github.com/a-rich/DJ-Tools/actions/workflows/pytest-coverage.yaml) and [pylint](https://github.com/a-rich/DJ-Tools/actions/workflows/pylint.yaml) Actions are triggered. For build checks to pass on the PR, both of these Actions must pass with `100%` or `10.00/10` in the case of `pylint`. If you're unable to pass the `pytest-coverage` Action, please open an issue. If you're not able to pass `pylint`, first attempt to correct the errors before resorting to [messages control](https://pylint.readthedocs.io/en/latest/user_guide/messages/message_control.html).

On `push` events to `releases/**`, the [deploy-dev-docs](https://github.com/a-rich/DJ-Tools/blob/pylint-check/.github/workflows/deploy-dev-docs.yaml) and the [release-dev](https://github.com/a-rich/DJ-Tools/blob/pylint-check/.github/workflows/release-dev.yaml) Actions are triggered.

`push` events to `main` trigger [deploy-prod-docs](https://github.com/a-rich/DJ-Tools/blob/pylint-check/.github/workflows/deploy-prod-docs.yaml) and [release-prod](https://github.com/a-rich/DJ-Tools/blob/pylint-check/.github/workflows/release-prod.yaml).

## Local testing (run from DJ-Tools repo)
### Setup dev environment:
```
pyenv virtualenv $(pyenv global) djtools-dev; pyenv activate djtools-dev; pip install -e ".[dev]"
```
### Test suite & coverage reporting:
```
pytest --cov --cov-report term-missing
```

### Linting check:
```
pylint $(git ls-files '*.py')
```