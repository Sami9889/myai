"""Dependency-free decoder transformer primitives for local inference."""
from __future__ import annotations
from dataclasses import dataclass
from math import cos, log, pi, sin, sqrt
from typing import Callable, Sequence
from .tensor_ops import Tensor, rms

@dataclass(frozen=True, slots=True)
class TransformerConfig:
    vocabulary_size: int
    context_length: int
    hidden_size: int
    layers: int
    heads: int
    intermediate_size: int
    rope_base: float = 10000.0
    epsilon: float = 1e-6

class Linear:
    def __init__(self, weight: Tensor, bias: Tensor | None = None) -> None:
        if len(weight.shape) != 2: raise ValueError("linear weights must be rank two")
        self.weight = weight; self.bias = bias
        if bias is not None and bias.shape != (weight.shape[0],): raise ValueError("bias shape mismatch")
    def __call__(self, vector: Sequence[float]) -> list[float]:
        if len(vector) != self.weight.shape[1]: raise ValueError("linear input mismatch")
        output = []
        for row in range(self.weight.shape[0]):
            value = sum(self.weight.data[row * self.weight.shape[1] + column] * vector[column] for column in range(self.weight.shape[1]))
            output.append(value + (self.bias.data[row] if self.bias else 0.0))
        return output

class RMSNorm:
    def __init__(self, weight: Sequence[float], epsilon: float = 1e-6) -> None: self.weight = list(weight); self.epsilon = epsilon
    def __call__(self, values: Sequence[float]) -> list[float]:
        if len(values) != len(self.weight): raise ValueError("norm width mismatch")
        scale = rms(values, self.epsilon); return [value / scale * self.weight[index] for index, value in enumerate(values)]

def apply_rope(vector: list[float], position: int, base: float = 10000.0) -> list[float]:
    result = vector.copy()
    for index in range(0, len(vector) - 1, 2):
        frequency = base ** (-index / len(vector)); angle = position * frequency
        result[index] = vector[index] * cos(angle) - vector[index + 1] * sin(angle)
        result[index + 1] = vector[index] * sin(angle) + vector[index + 1] * cos(angle)
    return result

class CausalSelfAttention:
    def __init__(self, query: Linear, key: Linear, value: Linear, output: Linear, heads: int, rope_base: float) -> None:
        if query.weight.shape[0] % heads: raise ValueError("hidden size must divide evenly among heads")
        self.query, self.key, self.value, self.output = query, key, value, output; self.heads = heads; self.head_width = query.weight.shape[0] // heads; self.rope_base = rope_base
    def __call__(self, sequence: Sequence[Sequence[float]]) -> list[list[float]]:
        if not sequence: return []
        queries = [apply_rope(self.query(row), position, self.rope_base) for position, row in enumerate(sequence)]
        keys = [apply_rope(self.key(row), position, self.rope_base) for position, row in enumerate(sequence)]
        values = [self.value(row) for row in sequence]; result: list[list[float]] = []
        for position, query in enumerate(queries):
            merged = [0.0] * (self.heads * self.head_width)
            for head in range(self.heads):
                start = head * self.head_width; scores = []
                for key_position in range(position + 1):
                    score = sum(query[start + j] * keys[key_position][start + j] for j in range(self.head_width)) / sqrt(self.head_width)
                    scores.append(score)
                maximum = max(scores); probabilities = [pow(2.718281828, max(-80.0, score - maximum)) for score in scores]; total = sum(probabilities) or 1.0
                for key_position, probability in enumerate(probabilities):
                    weight = probability / total
                    for j in range(self.head_width): merged[start + j] += weight * values[key_position][start + j]
            result.append(self.output(merged))
        return result

class FeedForward:
    def __init__(self, up: Linear, down: Linear) -> None: self.up, self.down = up, down
    def __call__(self, vector: Sequence[float]) -> list[float]:
        hidden = self.up(vector); activated = [value / (1.0 + pow(2.718281828, -max(-40.0, min(40.0, value)))) for value in hidden]
        return self.down(activated)

class TransformerBlock:
    def __init__(self, attention: CausalSelfAttention, feed_forward: FeedForward, attention_norm: RMSNorm, feed_forward_norm: RMSNorm) -> None:
        self.attention, self.feed_forward, self.attention_norm, self.feed_forward_norm = attention, feed_forward, attention_norm, feed_forward_norm
    def __call__(self, sequence: Sequence[Sequence[float]]) -> list[list[float]]:
        normalized = [self.attention_norm(row) for row in sequence]; attention = self.attention(normalized)
        residual = [[a + b for a, b in zip(row, update)] for row, update in zip(sequence, attention)]
        return [[a + b for a, b in zip(row, self.feed_forward(self.feed_forward_norm(row)))] for row in residual]

class DecoderTransformer:
    def __init__(self, config: TransformerConfig, embeddings: Tensor, blocks: Sequence[TransformerBlock], final_norm: RMSNorm, output: Linear) -> None:
        if embeddings.shape != (config.vocabulary_size, config.hidden_size): raise ValueError("embedding shape mismatch")
        self.config = config; self.embeddings = embeddings; self.blocks = list(blocks); self.final_norm = final_norm; self.output = output
    def forward(self, token_ids: Sequence[int]) -> list[list[float]]:
        if len(token_ids) > self.config.context_length: token_ids = token_ids[-self.config.context_length:]
        sequence = [self.embeddings.row(token) for token in token_ids]
        for block in self.blocks: sequence = block(sequence)
        return [self.output(self.final_norm(row)) for row in sequence]
    def logits(self, token_ids: Sequence[int]) -> list[float]:
        if not token_ids: raise ValueError("at least one token required")
        return self.forward(token_ids)[-1]
