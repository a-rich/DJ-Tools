# Contribution
If you wish to contribute to DJ Tools, please follow these development rules:
1. Development branches must:
    1. originate from and be linked to an associated Issue
    1. have a concise name for the feature or bugfix specifically targeted by that branch (e.g. `xml-track-randomization` or `improve-spotify-stability`)
1. Commit messages must:
    1. follow the [Conventional Commits](https://www.conventionalcommits.org/) standard
    1. include a `Why?` and `What?` section in the body describing the reason for and specifics of the commit
1. Commits must pass:
    1. tests with 100% code coverage
        - `push` and `pull_request` events trigger a [pytest-cov](https://github.com/a-rich/DJ-Tools/actions/workflows/test.yaml) Action
        - test by running the following command from the project root: `pytest --cov --cov-report term-missing`
        - open an issue if you're unable to pass tests with 100% coverage
    1. a pylint check with a 10/10 score
        - lint by running the following command from the project root: `find . -type f -name "*.py" | xargs pylint`
        - first attempt to correct the linting errors before adding [messages control](https://pylint.readthedocs.io/en/latest/user_guide/messages/message_control.html)