"""Training utilities for the local transformer."""
from __future__ import annotations
import math
import random
import sys
import time
from typing import Callable, Sequence
from .tensor_ops import Tensor
from .weights_parser import write_weights, WeightFile
from pathlib import Path

def _cross_entropy_loss(logits: list[float], target: int) -> tuple[float, list[float]]:
    max_logit = max(logits)
    exps = [math.exp(x - max_logit) for x in logits]
    total = sum(exps)
    log_sum = max_logit + math.log(total)
    loss = -logits[target] + log_sum
    probs = [x / total for x in exps]
    grad = [p - (1.0 if i == target else 0.0) for i, p in enumerate(probs)]
    return loss, grad

def _clip_gradients(data: list[float], max_norm: float = 1.0) -> None:
    total = sum(x * x for x in data)
    norm = math.sqrt(total)
    if norm > max_norm:
        scale = max_norm / norm
        for i in range(len(data)):
            data[i] *= scale

def _update_weight(data: list[float], grad: list[float], lr: float) -> None:
    for i in range(len(data)):
        data[i] -= lr * grad[i]
        if math.isfinite(data[i]):
            data[i] = max(-10.0, min(10.0, data[i]))
        else:
            data[i] = 0.0

def train_step(
    transformer,
    tokenizer,
    tokens: list[int],
    lr: float = 0.01,
) -> float:
    ctx = transformer.config.context_length
    total_loss = 0.0
    count = 0

    embeddings = transformer.embeddings
    blocks = transformer.blocks
    final_norm = transformer.final_norm
    output = transformer.output

    for step in range(len(tokens) - 1):
        start = max(0, step + 1 - ctx)
        chunk = tokens[start:step + 1]
        target = tokens[step + 1]

        sequence = [embeddings.row(t) for t in chunk]
        for block in blocks:
            normalized = [block.attention_norm(row) for row in sequence]
            attention = block.attention(normalized)
            residual = [[a + b for a, b in zip(row, update)] for row, update in zip(sequence, attention)]
            sequence = [[a + b for a, b in zip(row, block.feed_forward(block.feed_forward_norm(row)))] for row in residual]
        hidden = final_norm(sequence[-1])
        logits = output(hidden)

        loss, grad = _cross_entropy_loss(logits, target)
        total_loss += loss
        count += 1

        _clip_gradients(grad, max_norm=1.0)
        for i in range(output.weight.shape[0]):
            for j in range(output.weight.shape[1]):
                idx = i * output.weight.shape[1] + j
                output.weight.data[idx] -= lr * grad[i] * hidden[j]
                if math.isfinite(output.weight.data[idx]):
                    output.weight.data[idx] = max(-10.0, min(10.0, output.weight.data[idx]))
                else:
                    output.weight.data[idx] = 0.0
        if output.bias is not None:
            for i in range(len(grad)):
                output.bias.data[i] -= lr * grad[i]
                if math.isfinite(output.bias.data[i]):
                    output.bias.data[i] = max(-10.0, min(10.0, output.bias.data[i]))
                else:
                    output.bias.data[i] = 0.0

        hidden_grad = [0.0] * len(hidden)
        for i in range(len(hidden_grad)):
            for j in range(len(grad)):
                hidden_grad[i] += grad[j] * output.weight.data[j * output.weight.shape[1] + i]

        for i in range(len(hidden_grad)):
            for j in range(len(sequence[-1])):
                idx = chunk[-1] * embeddings.shape[1] + j
                embeddings.data[idx] -= lr * hidden_grad[i] * sequence[-1][j]
                if math.isfinite(embeddings.data[idx]):
                    embeddings.data[idx] = max(-10.0, min(10.0, embeddings.data[idx]))
                else:
                    embeddings.data[idx] = 0.0

    return total_loss / max(1, count)

def _log_memory(label: str = '') -> None:
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF)
        mem_kb = usage.ru_maxrss
        if sys.platform == 'linux':
            mem_mb = mem_kb / 1024
        else:
            mem_mb = mem_kb / 1024 / 1024
        print(f'[mem] {label} rss={mem_mb:.1f} MB', flush=True)
    except Exception:
        pass

def train_on_text(
    model_path: str | Path,
    tokenizer,
    texts: list[str],
    epochs: int = 3,
    lr: float = 0.01,
    seed: int | None = None,
    progress_callback=None,
) -> None:
    rng = random.Random(seed)
    model_path = Path(model_path)
    _log_memory('before_load')
    with WeightFile(model_path) as wf:
        records = {name: wf.read(name) for name in wf.names()}
    _log_memory('after_load')

    total_texts = len(texts)
    transformer = _build_transformer_from_records(records, tokenizer)
    step_times: list[float] = []

    for epoch in range(epochs):
        rng.shuffle(texts)
        epoch_loss = 0.0
        steps = 0
        epoch_start = time.time()
        if progress_callback:
            progress_callback('epoch_start', epoch=epoch + 1, epochs=epochs, total_texts=total_texts)
        for text_index, text in enumerate(texts, 1):
            tokens = tokenizer.encode(text)
            if len(tokens) < 2:
                continue
            step_start = time.time()
            loss = train_step(transformer, tokenizer, tokens, lr=lr)
            step_elapsed = time.time() - step_start
            step_times.append(step_elapsed)
            if len(step_times) > 20:
                step_times.pop(0)
            epoch_loss += loss
            steps += 1
            if progress_callback:
                avg_step = sum(step_times) / len(step_times)
                progress_callback('step', epoch=epoch + 1, epochs=epochs, text_index=text_index, total_texts=total_texts, loss=loss, step_time=step_elapsed, avg_step_time=avg_step)
        avg = epoch_loss / max(1, steps)
        epoch_elapsed = time.time() - epoch_start
        if progress_callback:
            progress_callback('epoch_end', epoch=epoch + 1, epochs=epochs, loss=avg, elapsed=epoch_elapsed, steps=steps)
        else:
            print(f'epoch {epoch + 1}/{epochs} loss={avg:.4f} steps={steps} time={epoch_elapsed:.1f}s')

    _log_memory('before_save')
    write_weights(model_path, records)
    _log_memory('after_save')

def _build_transformer_from_records(records, tokenizer):
    from core_engine.transformer import TransformerConfig, DecoderTransformer, TransformerBlock, CausalSelfAttention, FeedForward, Linear, RMSNorm
    vocab_size = tokenizer.vocabulary_size
    ctx = 64
    hidden = 8
    layers = 1
    heads = 2

    embeddings = _first(records, 'tok_embeddings', 'embeddings', 'word_embeddings')
    final_norm_data = _first(records, 'final_norm', 'ln_f', 'layer_norm')
    final_norm = RMSNorm(final_norm_data.data)
    output_weight = _first(records, 'lm_head', 'output', 'word_embeddings')
    output = Linear(output_weight)

    blocks = []
    for i in range(layers):
        p = f'layers.{i}'
        q = _first(records, f'{p}.attention.query_proj', f'{p}.query', f'{p}.attn.q_proj')
        k = _first(records, f'{p}.attention.key_proj', f'{p}.key', f'{p}.attn.k_proj')
        v = _first(records, f'{p}.attention.value_proj', f'{p}.value', f'{p}.attn.v_proj')
        o = _first(records, f'{p}.attention.output_proj', f'{p}.output', f'{p}.attn.o_proj')
        attention = CausalSelfAttention(Linear(q), Linear(k), Linear(v), Linear(o), heads=heads, rope_base=10000.0)
        up = _first(records, f'{p}.feed_forward.w1', f'{p}.up_proj', f'{p}.mlp.gate_proj')
        down = _first(records, f'{p}.feed_forward.w2', f'{p}.down_proj', f'{p}.mlp.down_proj')
        feed_forward = FeedForward(Linear(up), Linear(down))
        attn_norm = _first(records, f'{p}.attention_norm', f'{p}.ln1', f'{p}.ln_attn')
        ffn_norm = _first(records, f'{p}.feed_forward_norm', f'{p}.ln2', f'{p}.ln_mlp')
        blocks.append(TransformerBlock(attention, feed_forward, RMSNorm(attn_norm.data), RMSNorm(ffn_norm.data)))

    config = TransformerConfig(vocabulary_size=vocab_size, context_length=ctx, hidden_size=hidden, layers=layers, heads=heads, intermediate_size=hidden * 4)
    return DecoderTransformer(config, embeddings, blocks, final_norm, output)

def _first(records, *names):
    for name in names:
        if name in records:
            return records[name]
    return None
