# Contributing

Thanks for your interest in improving WhoOwns. Contributions should stay lean: propose focused changes, explain them clearly, and show how they were tested.

## How to Contribute

1. Fork the repository.
2. Create a branch in your fork for the change.
3. Make a focused update.
4. Open a pull request against this repository.

Keep pull requests small enough to review in one pass. Separate unrelated changes into separate PRs.

## Pull Request Expectations

Every PR should include:

- A clear summary of what changed.
- Why the change is needed.
- Any tradeoffs, assumptions, or follow-up work.
- Proof that the change was tested, including the exact commands run and the result.

For documentation-only changes, describe how you reviewed the rendered Markdown. For code changes, include automated test output when available.

Example testing note:

```text
Tested with:
- make test
- make lint

Result: both passed locally.
```

If a change cannot be tested yet, explain why and describe the manual validation performed.

## Style Guidelines

Use concise, direct language in documentation. Prefer examples over long explanations. Keep terminology consistent with `PRD.md`, especially domain terms such as `Team`, `Service`, `ServiceOwnership`, and `Resource`.

For code, follow the conventions already present in the repository. If no convention exists yet, choose the simplest standard for the language or framework being introduced and document the command needed to format or lint it.

## Review Criteria

Pull requests are easier to review when they:

- Solve one clear problem.
- Avoid unrelated refactors.
- Include tests or validation evidence.
- Update documentation when behavior or usage changes.
- Preserve the project goal: simple ownership resolution.

Maintainers may ask for changes before merging. The goal is not process for its own sake; it is to keep the project understandable and reliable.
