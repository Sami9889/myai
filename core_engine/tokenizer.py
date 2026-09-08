"""Byte-level BPE tokenizer with deterministic fallback behavior."""
from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

@dataclass(frozen=True, slots=True)
class Token:
    id: int
    text: bytes

class ByteBPETokenizer:
    def __init__(self, vocabulary: dict[str, int] | None = None, merges: Iterable[tuple[str, str]] = ()) -> None:
        self.vocabulary = vocabulary or {chr(index): index for index in range(256)}
        self.inverse = {value: key.encode("utf-8", "surrogateescape") for key, value in self.vocabulary.items()}
        self.ranks = {tuple(pair): rank for rank, pair in enumerate(merges)}
        self.unknown_id = self.vocabulary.get("<unk>", 0)

    @classmethod
    def from_json(cls, path: str | Path) -> "ByteBPETokenizer":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        vocabulary = {str(key): int(value) for key, value in payload["vocab"].items()}
        merges = [tuple(str(line).split()) for line in payload.get("merges", [])]
        return cls(vocabulary, merges)

    def _initial(self, data: bytes) -> list[str]: return [bytes([value]).decode("latin1") for value in data]
    def _merge_once(self, symbols: list[str]) -> list[str]:
        best: tuple[int, int, tuple[str, str]] | None = None
        for index in range(len(symbols) - 1):
            pair = (symbols[index], symbols[index + 1]); rank = self.ranks.get(pair)
            if rank is not None and (best is None or rank < best[0]): best = (rank, index, pair)
        if best is None: return symbols
        _, index, pair = best
        return symbols[:index] + [pair[0] + pair[1]] + symbols[index + 2:]

    def encode_bytes(self, data: bytes) -> list[int]:
        symbols = self._initial(data)
        while True:
            merged = self._merge_once(symbols)
            if merged == symbols: break
            symbols = merged
        result: list[int] = []
        for symbol in symbols:
            result.append(self.vocabulary.get(symbol, self.unknown_id))
        return result

    def encode(self, text: str) -> list[int]: return self.encode_bytes(text.encode("utf-8", "surrogatepass"))
    def decode(self, ids: Iterable[int]) -> str:
        data = b"".join(self.inverse.get(int(token), b"<unk>") for token in ids)
        return data.decode("utf-8", "replace")
    def token_text(self, token_id: int) -> bytes: return self.inverse.get(token_id, b"<unk>")
    @property
    def vocabulary_size(self) -> int: return len(self.vocabulary)
