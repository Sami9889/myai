"""Deterministic, configurable token sampling."""
from __future__ import annotations
from dataclasses import dataclass
from math import exp
import random
from typing import Sequence

@dataclass(slots=True)
class SamplingConfig:
    temperature: float = 0.7
    top_k: int = 40
    top_p: float = 0.9
    repetition_penalty: float = 1.1
    seed: int | None = None

class Sampler:
    def __init__(self, config: SamplingConfig | None = None) -> None:
        self.config = config or SamplingConfig(); self.random = random.Random(self.config.seed)
    def _probabilities(self, logits: Sequence[float], history: Sequence[int]) -> list[tuple[int, float]]:
        if not logits: raise ValueError("cannot sample empty logits")
        temperature = max(1e-5, self.config.temperature)
        adjusted = list(float(value) for value in logits)
        penalty = max(1e-6, self.config.repetition_penalty)
        for token in set(history):
            if 0 <= token < len(adjusted): adjusted[token] = adjusted[token] / penalty if adjusted[token] > 0 else adjusted[token] * penalty
        maximum = max(adjusted); values = [exp(max(-80.0, min(80.0, value / temperature - maximum / temperature))) for value in adjusted]
        total = sum(values) or 1.0
        ranked = sorted(((index, value / total) for index, value in enumerate(values)), key=lambda pair: pair[1], reverse=True)
        if self.config.top_k > 0: ranked = ranked[:self.config.top_k]
        selected: list[tuple[int, float]] = []; cumulative = 0.0
        for item in ranked:
            selected.append(item); cumulative += item[1]
            if cumulative >= min(1.0, max(0.0, self.config.top_p)): break
        normalization = sum(value for _, value in selected) or 1.0
        return [(index, value / normalization) for index, value in selected]
    def sample(self, logits: Sequence[float], history: Sequence[int] = ()) -> int:
        probabilities = self._probabilities(logits, history); target = self.random.random(); cumulative = 0.0
        for token, probability in probabilities:
            cumulative += probability
            if target <= cumulative: return token
        return probabilities[-1][0]
    def greedy(self, logits: Sequence[float]) -> int:
        if not logits: raise ValueError("cannot choose from empty logits")
        return max(range(len(logits)), key=logits.__getitem__)
