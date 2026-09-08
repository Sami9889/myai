"""Strict parser for a small self-describing local .bin tensor format."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import struct
from typing import Iterator
from .tensor_ops import Tensor

MAGIC = b"MYAIW01\0"

@dataclass(frozen=True, slots=True)
class WeightRecord:
    name: str
    shape: tuple[int, ...]
    offset: int
    count: int

class WeightFile:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path); self.records: dict[str, WeightRecord] = {}
        self._file = self.path.open("rb")
        self._parse()
    def _read(self, count: int) -> bytes:
        data = self._file.read(count)
        if len(data) != count: raise ValueError("truncated weight file")
        return data
    def _parse(self) -> None:
        if self._read(8) != MAGIC: raise ValueError("invalid MYAI weight magic")
        count = struct.unpack("<I", self._read(4))[0]
        for _ in range(count):
            name_length = struct.unpack("<H", self._read(2))[0]
            name = self._read(name_length).decode("utf-8")
            rank = struct.unpack("<B", self._read(1))[0]
            shape = tuple(struct.unpack("<I", self._read(4))[0] for _ in range(rank))
            size = 1
            for dimension in shape: size *= dimension
            offset = self._file.tell(); self._file.seek(size * 4, 1)
            self.records[name] = WeightRecord(name, shape, offset, size)
    def names(self) -> Iterator[str]: return iter(self.records)
    def read(self, name: str) -> Tensor:
        record = self.records[name]; self._file.seek(record.offset)
        data = self._read(record.count * 4)
        return Tensor(record.shape, list(struct.unpack(f"<{record.count}f", data)))
    def close(self) -> None: self._file.close()
    def __enter__(self) -> "WeightFile": return self
    def __exit__(self, *_: object) -> None: self.close()

def write_weights(path: str | Path, tensors: dict[str, Tensor]) -> None:
    target = Path(path)
    with target.open("wb") as stream:
        stream.write(MAGIC); stream.write(struct.pack("<I", len(tensors)))
        for name, tensor in tensors.items():
            encoded = name.encode("utf-8")
            if len(encoded) > 65535 or len(tensor.shape) > 255: raise ValueError("weight metadata too large")
            stream.write(struct.pack("<H", len(encoded))); stream.write(encoded)
            stream.write(struct.pack("<B", len(tensor.shape)))
            for dimension in tensor.shape: stream.write(struct.pack("<I", dimension))
            stream.write(struct.pack(f"<{len(tensor.data)}f", *tensor.data))
