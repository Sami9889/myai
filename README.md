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

## Development

```sh
make package
make lint
```

High-risk commands require an explicit confirmation gate. Network access is disabled by default.

## Coding Prompt Pack

Workspace-shared prompts live in `.github/prompts/` as a 50-workflow coding pack covering normal assistance, architecture, APIs, core engine work, orchestration, tools, CLI UX, security, debugging, review, testing, release, model weights, performance, Git, operations, and resilience.
