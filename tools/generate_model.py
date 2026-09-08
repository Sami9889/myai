from __future__ import annotations
import json
from pathlib import Path
from core_engine.tensor_ops import Tensor
from core_engine.weights_parser import write_weights

ROOT = Path(__file__).resolve().parent.parent

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

hidden_size = 64
vocab_size = len(vocab)
layers = 2
heads = 2
context_length = 128

weights: dict[str, Tensor] = {}

weights["tok_embeddings"] = Tensor((vocab_size, hidden_size), [0.0] * (vocab_size * hidden_size))
weights["final_norm"] = Tensor((hidden_size,), [1.0] * hidden_size)
weights["lm_head"] = Tensor((vocab_size, hidden_size), [0.0] * (vocab_size * hidden_size))

for i in range(layers):
    p = f"layers.{i}"
    weights[f"{p}.attention.query_proj"] = Tensor((hidden_size, hidden_size), [0.0] * (hidden_size * hidden_size))
    weights[f"{p}.attention.key_proj"] = Tensor((hidden_size, hidden_size), [0.0] * (hidden_size * hidden_size))
    weights[f"{p}.attention.value_proj"] = Tensor((hidden_size, hidden_size), [0.0] * (hidden_size * hidden_size))
    weights[f"{p}.attention.output_proj"] = Tensor((hidden_size, hidden_size), [0.0] * (hidden_size * hidden_size))
    weights[f"{p}.feed_forward.w1"] = Tensor((hidden_size * 4, hidden_size), [0.0] * (hidden_size * 4 * hidden_size))
    weights[f"{p}.feed_forward.w2"] = Tensor((hidden_size, hidden_size * 4), [0.0] * (hidden_size * hidden_size * 4))
    weights[f"{p}.attention_norm"] = Tensor((hidden_size,), [1.0] * hidden_size)
    weights[f"{p}.feed_forward_norm"] = Tensor((hidden_size,), [1.0] * hidden_size)

weights_path = model_dir / "local_model.bin"
write_weights(weights_path, weights)

config = {
    "model": {
        "path": str(weights_path),
        "tokenizer": str(tokenizer_path),
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
        "allow_network": False,
        "workspace": "."
    }
}

config_path = ROOT / "config.json"
config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

print(f"Created model: {weights_path}")
print(f"Created tokenizer: {tokenizer_path}")
print(f"Updated config: {config_path}")
