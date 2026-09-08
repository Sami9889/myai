# myai Engineering Rules

This repository is a zero-cloud, local-only coding agent. Preserve that invariant: do not add OpenAI, Anthropic, Ollama, llama.cpp, Transformers, PyTorch, TensorFlow, telemetry, or network inference clients.

Use Python standard library APIs unless a dependency is explicitly approved. Keep workspace paths confined, high-risk commands gated, writes atomic, and model loading explicit. Never claim neural generation is active when no compatible local weights are configured.

Before editing, identify the owning code path and one focused validation. After editing, run the narrowest executable check available. Preserve user changes, avoid generated metadata, and keep public APIs stable unless the task requires a change.

Prefer small typed modules, deterministic behavior, actionable errors, and operational documentation. Do not inflate files to satisfy line counts; implement real behavior and state limitations plainly.
