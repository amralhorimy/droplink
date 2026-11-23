# Contributing to DropLink

Thanks for considering a contribution. DropLink is an educational backend project, so contributions that improve correctness, clarity, reproducibility, and learning value are especially welcome.

## Good first contributions

- Improve English or Arabic documentation.
- Add focused unit or API tests.
- Improve a lab so it demonstrates a backend concept more clearly.
- Fix a reproducible bug.
- Suggest a small feature with a clear use case.

## Before opening a pull request

1. Open an issue first for larger changes so we can agree on the scope.
2. Keep changes focused; avoid unrelated refactors.
3. Add or update tests for behavior changes.
4. Update both English and Arabic docs when the change affects documented behavior.
5. Never commit secrets, local environment files, credentials, or real user data.

## Local checks

Run the checks relevant to your change:

```bash
make test
make e2e
make race
```

The end-to-end and race labs require the Docker Compose stack to be running.

## Pull request description

Please include:
- What problem does this solve?
- Why is this approach appropriate?
- How did you test it?
- Are there documentation or configuration changes?

By contributing, you agree that your contributions are provided under the repository's MIT license.