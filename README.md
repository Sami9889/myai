# myai

`myai` is a local-only coding and general-intelligence CLI built from Java's standard library. It has no cloud API client and no dependency on external AI backends.

## Install

```sh
./install.sh
myai
```

## Automatic Updates

To check for updates:

```sh
myai-update --once
```

## Productivity Commands

```sh
myai diagnostics
myai walk '*.java'
myai read README.md
myai write notes.txt "Created at the current local time"
myai lint core_engine/Tokenizer.java
myai todo add "Review model configuration"
myai todo list
myai todo done 1
myai search "transformer attention"
myai time
myai status
myai help
myai repo status
myai repo add . --confirm
myai repo commit "Describe the change" --confirm
myai repo push --confirm
```

File writes report the edited path and local timestamp. TODOs persist in `.myai-tasks.json`, and `search` indexes local documentation and source only; it does not contact Google or any external service.

Repository publishing is guarded: `repo status` is read-only, while `repo add`, `repo commit`, and `repo push` require `--confirm`. Pushes target the current branch and never force-push or rewrite history.

## Natural Requests

You do not need to memorize command syntax. The CLI understands requests such as:

```text
read README.md
show Java files
add a task for review the tokenizer
search help for attention
check core_engine/Tokenizer.java
what changed
install this repo yes
```

Natural requests use the same repository-scoped tools as exact commands.

You can also ask how a local class works, ask for a Git status/diff, or say “learn from this workspace.” Coding questions search current source and documentation as needed. Learning uses a bounded local corpus and does not contact the network.

### Python and Git Reference

```python
def normalize_names(names: list[str]) -> list[str]:
	return [name.strip().lower() for name in names if name.strip()]

try:
	result = normalize_names([" Ada ", ""])
except ValueError as error:
	print(error)
```

Python blocks are defined by indentation. Functions use `def`; loops use `for` or `while`; comprehensions use `[value for item in items if condition]`; exceptions use `try` and `except`.

Common read-only Git checks are `git status --short --branch`, `git diff`, `git log --oneline -10`, and `git branch --show-current`. Changes are staged with `git add -- PATH`, recorded with `git commit -m MESSAGE`, and sent with `git push`; repository-changing actions in myai require explicit confirmation.

## Development

```sh
make package
make lint
```

High-risk commands require an explicit confirmation gate. Network access is disabled by default.

The checked-in model is randomly initialized, not a pretrained coding model. The current trainer optimizes the output projection only; it does not backpropagate through transformer layers and cannot teach the model all programming knowledge. Workspace search is the reliable source of project-specific answers.

## Coding Prompt Pack

Workspace-shared prompts live in `.github/prompts/` as a 50-workflow coding pack covering normal assistance, architecture, APIs, core engine work, orchestration, tools, CLI UX, security, debugging, review, testing, release, model weights, performance, Git, operations, and resilience.
