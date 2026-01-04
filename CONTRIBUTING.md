# Contribution
If you wish to contribute to DJ Tools, please follow these development rules:
1. Development branches must:
    1. be linked to an Issue
    1. branch from `release/*`
    1. have a concise name for the feature or bugfix specifically targeted by that branch (e.g. `xml-track-randomization` or `improve-spotify-stability`)
1. Commits must:
    1. have messages that follow the [Conventional Commits](https://www.conventionalcommits.org/) standard
    1. (if non-trivial) have messages that include a `Why?` and `What?` section in the body describing the reason for and specifics of the commit
    1. (if relevant) include updates to the [docs](https://github.com/a-rich/DJ-Tools/tree/main/docs)

## CI
On `push` events (with `**.py` changes) to feature branches, the [format](https://github.com/a-rich/DJ-Tools/actions/workflows/format.yaml) Action will run the [black code formatter](https://github.com/psf/black) and commit changes if there are any.

On `pull_request` events (with `src/**.py` or `tests/**.py` changes) the [test-lint](https://github.com/a-rich/DJ-Tools/actions/workflows/test-lint.yaml) Action is triggered. For build checks to pass on the PR, this Action must have `100%` test passing and coverage and a `10.00/10` linting score:
- if you're unable to pass tests with `100%` coverage, please open an issue
- if you're not getting a `10.00/10` lint score, first attempt to correct the errors before resorting to [messages control](https://pylint.readthedocs.io/en/latest/user_guide/messages/message_control.html)

On `push` events to `release/**` the following Actions are triggered:
- [release-dev](https://github.com/a-rich/DJ-Tools/blob/pylint-check/.github/workflows/release-dev.yaml) (with `src/**.py` changes)
- [deploy-dev-docs](https://github.com/a-rich/DJ-Tools/blob/pylint-check/.github/workflows/deploy-dev-docs.yaml) (with `src/**.py` or `docs/**.md` changes)

On `push` events to `main`, for the same file change patterns, the [deploy-prod-docs](https://github.com/a-rich/DJ-Tools/blob/pylint-check/.github/workflows/deploy-prod-docs.yaml) and [release-prod](https://github.com/a-rich/DJ-Tools/blob/pylint-check/.github/workflows/release-prod.yaml) Actions are triggered.

## Local testing (run from DJ-Tools repo)
### Setup dev environment:
```
uv sync && uv run pre-commit install
```

### pre-commit hooks:
Installing `pre-commit` enables testing, linting, and formatting checks defined in [.pre-commit-config.yaml](./.pre-commit-config.yaml).
You can run these same checks at any time with the following commands:

#### Test with pytest
```
uv run pytest --cov --cov-report term-missing
```
#### Lint with pylint
```
uv run pylint $(git ls-files '*.py')
```
#### Format code with black
```
uv run black .
```
