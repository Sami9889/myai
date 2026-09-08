# myai

`myai` is a local-only coding and general-intelligence CLI built from Python's standard library. It has no cloud API client and no dependency on Ollama, llama.cpp, Transformers, PyTorch, or TensorFlow.

## Install

```sh
./install.sh
source .venv/bin/activate
myai
```

## Automatic Updates

To copy the repository and install the CLI in a separate home directory:

```sh
rsync -a --exclude='.venv' --exclude='__pycache__' --exclude='*.egg-info' /workspaces/myai/ "$HOME/myai/"
cd "$HOME/myai"
./install.sh
```

To check for a new `main` commit once:

```sh
myai-update --once
```

To keep watching and automatically fast-forward/reinstall every five minutes:

```sh
myai-update --interval 300
```

The updater skips updates when local changes exist and never performs a force reset.

## Productivity Commands

```sh
myai diagnostics
myai walk '*.py'
myai read README.md
myai write notes.txt "Created at the current local time"
myai lint core_engine/tokenizer.py
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

File writes report the edited path and local timestamp. TODOs persist in
`.myai-tasks.json`, and `search` indexes local documentation and source only;
it does not contact Google or any external service.

Repository publishing is guarded: `repo status` is read-only, while `repo
add`, `repo commit`, and `repo push` require `--confirm`. Pushes target the
current branch and never force-push or rewrite history.

## Natural Requests

You do not need to memorize command syntax. The CLI understands requests such
as:

```text
read README.md
show Python files
add a task for review the tokenizer
search help for attention
check core_engine/tokenizer.py
what changed
install this repo yes
```

Natural requests use the same repository-scoped tools as exact commands. Read,
write, and edit operations are allowed anywhere inside the selected workspace
repository. Paths outside that repository are rejected. Installation,
commits, and pushes require explicit confirmation.

You can also speak normally:

```text
Hey, are you there?
Tell me what you can do.
Please read the README and tell me what this project is.
I am here, what should we work on?
```

The runtime accepts raw model weights through the documented binary parser, but it does not ship model weights. Configure `config.json` with a compatible local model before requesting neural generation. Without weights, the CLI remains useful for safe file inspection, AST analysis, diagnostics, and deterministic tool orchestration.

## Development

```sh
make lint
```

High-risk commands require an explicit confirmation gate. Network access is disabled by default.

## Coding Prompt Pack

Workspace-shared prompts live in `.github/prompts/` as a 50-workflow coding
pack covering normal assistance, architecture, APIs, core engine work,
orchestration, tools, CLI UX, security, debugging, review, testing, release,
model weights, performance, Git, operations, and resilience. The always-on repository
rules are in `.github/copilot-instructions.md`. In VS Code, invoke a focused
workflow from the prompt picker, such as `/coding-agent`, `/debug`, or
`/review`.
