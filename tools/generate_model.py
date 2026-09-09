from __future__ import annotations
import json
import random
from pathlib import Path
from core_engine.tensor_ops import Tensor
from core_engine.weights_parser import write_weights

ROOT = Path(__file__).resolve().parent.parent
random.seed(42)

def rand(shape: tuple[int, ...], scale: float = 0.02) -> Tensor:
    size = 1
    for d in shape: size *= d
    return Tensor(shape, [random.uniform(-scale, scale) for _ in range(size)])

vocab = {chr(i): i for i in range(256)}
vocab["<unk>"] = 256
vocab["<eos>"] = 257

tokenizer = {
    "vocab": vocab,
    "merges": []
}

model_dir = ROOT / "models"
model_dir.mkdir(exist_ok=True)

tokenizer_path = model_dir / "tokenizer.json"
tokenizer_path.write_text(json.dumps(tokenizer, indent=2), encoding="utf-8")

hidden_size = 8
vocab_size = len(vocab)
layers = 1
heads = 2
context_length = 16

weights: dict[str, Tensor] = {}

weights["tok_embeddings"] = rand((vocab_size, hidden_size))
weights["final_norm"] = Tensor((hidden_size,), [1.0] * hidden_size)
weights["lm_head"] = rand((vocab_size, hidden_size))

for i in range(layers):
    p = f"layers.{i}"
    weights[f"{p}.attention.query_proj"] = rand((hidden_size, hidden_size))
    weights[f"{p}.attention.key_proj"] = rand((hidden_size, hidden_size))
    weights[f"{p}.attention.value_proj"] = rand((hidden_size, hidden_size))
    weights[f"{p}.attention.output_proj"] = rand((hidden_size, hidden_size))
    weights[f"{p}.feed_forward.w1"] = rand((hidden_size * 4, hidden_size))
    weights[f"{p}.feed_forward.w2"] = rand((hidden_size, hidden_size * 4))
    weights[f"{p}.attention_norm"] = Tensor((hidden_size,), [1.0] * hidden_size)
    weights[f"{p}.feed_forward_norm"] = Tensor((hidden_size,), [1.0] * hidden_size)

weights_path = model_dir / "local_model.bin"
write_weights(weights_path, weights)

config = {
    "model": {
        "path": "models/local_model.bin",
        "tokenizer": "models/tokenizer.json",
        "context_length": context_length,
        "hidden_size": hidden_size,
        "layers": layers,
        "heads": heads
    },
    "runtime": {
        "max_steps": 32,
        "temperature": 0.7,
        "top_k": 40,
        "top_p": 0.9
    },
    "security": {
        "confirm_shell": True,
        "allow_network": True,
        "workspace": "."
    },
    "coding_prompts": [
        "write a Python function to sort a list",
        "implement a linked list in Python",
        "create a REST API endpoint in Flask",
        "write a Dockerfile for a Python app",
        "refactor this function for readability",
        "add type hints to this module",
        "write unit tests for this class",
        "optimize this SQL query",
        "implement a binary search algorithm",
        "create a React component for a todo list",
        "write a shell script to backup a database",
        "implement a retry decorator with exponential backoff",
        "create a middleware for authentication",
        "write a CSV parser with error handling",
        "implement a priority queue using a heap"
    ]
}

config_path = ROOT / "config.json"
config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

print(f"Created model: {weights_path}")
print(f"Created tokenizer: {tokenizer_path}")
print(f"Updated config: {config_path}")
