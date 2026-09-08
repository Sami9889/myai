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

The runtime accepts raw model weights through the documented binary parser, but it does not ship model weights. Configure `config.json` with a compatible local model before requesting neural generation. Without weights, the CLI remains useful for safe file inspection, AST analysis, diagnostics, and deterministic tool orchestration.

## Development

```sh
make lint
```

High-risk commands require an explicit confirmation gate. Network access is disabled by default.
