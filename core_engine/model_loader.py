from __future__ import annotations
from pathlib import Path
from typing import Callable
from .tokenizer import ByteBPETokenizer
from .transformer import (
    TransformerConfig, DecoderTransformer, TransformerBlock,
    CausalSelfAttention, FeedForward, Linear, RMSNorm
)
from .weights_parser import WeightFile
from .tensor_ops import Tensor
from .sampler import Sampler, SamplingConfig

def _first(records: dict[str, Tensor], *names: str) -> Tensor | None:
    for name in names:
        if name in records:
            return records[name]
    return None

def load_local_model(config: dict) -> Callable[[list[dict[str, str]]], str] | None:
    model_cfg = config.get("model", {})
    path = model_cfg.get("path", "")
    if not path:
        return None

    path = Path(path)
    if not path.is_file():
        return None

    tokenizer_path = model_cfg.get("tokenizer")
    if tokenizer_path:
        tokenizer = ByteBPETokenizer.from_json(tokenizer_path)
    else:
        candidate = path.parent / "tokenizer.json"
        if candidate.exists():
            tokenizer = ByteBPETokenizer.from_json(candidate)
        else:
            tokenizer = ByteBPETokenizer()

    runtime = config.get("runtime", {})

    with WeightFile(path) as wf:
        records = {name: wf.read(name) for name in wf.names()}

    vocab_size = tokenizer.vocabulary_size
    ctx = int(model_cfg.get("context_length", 2048))
    hidden = int(model_cfg.get("hidden_size", 256))
    layers = int(model_cfg.get("layers", 4))
    heads = int(model_cfg.get("heads", 4))
    intermediate = int(model_cfg.get("intermediate_size", hidden * 4))

    transformer_config = TransformerConfig(
        vocabulary_size=vocab_size,
        context_length=ctx,
        hidden_size=hidden,
        layers=layers,
        heads=heads,
        intermediate_size=intermediate,
    )

    embeddings = _first(records, "tok_embeddings", "embeddings", "word_embeddings")
    if embeddings is None:
        raise ValueError("missing embeddings weight")

    final_norm_data = _first(records, "final_norm", "ln_f", "layer_norm")
    if final_norm_data is None:
        raise ValueError("missing final norm weight")
    final_norm = RMSNorm(final_norm_data.data)

    output_weight = _first(records, "lm_head", "output", "word_embeddings")
    if output_weight is None:
        output_weight = embeddings
    output = Linear(output_weight)

    blocks: list[TransformerBlock] = []
    for i in range(layers):
        p = f"layers.{i}"

        q = _first(records, f"{p}.attention.query_proj", f"{p}.query", f"{p}.attn.q_proj")
        k = _first(records, f"{p}.attention.key_proj", f"{p}.key", f"{p}.attn.k_proj")
        v = _first(records, f"{p}.attention.value_proj", f"{p}.value", f"{p}.attn.v_proj")
        o = _first(records, f"{p}.attention.output_proj", f"{p}.output", f"{p}.attn.o_proj")
        if any(x is None for x in [q, k, v, o]):
            raise ValueError(f"missing attention weights for layer {i}")

        attention = CausalSelfAttention(
            Linear(q), Linear(k), Linear(v), Linear(o),
            heads=heads,
            rope_base=transformer_config.rope_base,
        )

        up = _first(records, f"{p}.feed_forward.w1", f"{p}.up_proj", f"{p}.mlp.gate_proj")
        down = _first(records, f"{p}.feed_forward.w2", f"{p}.down_proj", f"{p}.mlp.down_proj")
        if any(x is None for x in [up, down]):
            raise ValueError(f"missing feed forward weights for layer {i}")
        feed_forward = FeedForward(Linear(up), Linear(down))

        attn_norm = _first(records, f"{p}.attention_norm", f"{p}.ln1", f"{p}.ln_attn")
        ffn_norm = _first(records, f"{p}.feed_forward_norm", f"{p}.ln2", f"{p}.ln_mlp")
        if attn_norm is None or ffn_norm is None:
            raise ValueError(f"missing norm weights for layer {i}")

        blocks.append(TransformerBlock(
            attention,
            feed_forward,
            RMSNorm(attn_norm.data),
            RMSNorm(ffn_norm.data),
        ))

    transformer = DecoderTransformer(transformer_config, embeddings, blocks, final_norm, output)
    sampler = Sampler(SamplingConfig(
        temperature=runtime.get("temperature", 0.7),
        top_k=runtime.get("top_k", 40),
        top_p=runtime.get("top_p", 0.9),
    ))

    EOS_TOKEN = tokenizer.vocabulary.get("<eos>")

    def _is_readable(text: str) -> bool:
        if not text:
            return False
        text = text.strip()
        if not text:
            return False
        printable = sum(ch.isprintable() or ch.isspace() for ch in text)
        return printable / max(1, len(text)) >= 0.7

    def model(messages: list[dict[str, str]]) -> str | None:
        prompt = "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}"
            for m in messages
        )
        token_ids = tokenizer.encode(prompt)
        max_new = int(runtime.get("max_new_tokens", 32))
        generated = list(token_ids)

        for _ in range(max_new):
            if len(generated) > ctx:
                generated = generated[-ctx:]
            logits = transformer.logits(generated)
            next_id = sampler.sample(logits, generated)
            generated.append(next_id)
            if EOS_TOKEN is not None and next_id == EOS_TOKEN:
                break

        new_ids = generated[len(token_ids):]
        text = tokenizer.decode(new_ids)
        return text if _is_readable(text) else None

    return model
