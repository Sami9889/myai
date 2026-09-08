"""Small, dependency-free dense tensor operations used by the local engine."""
from __future__ import annotations
from dataclasses import dataclass
from math import exp, sqrt
from mmap import mmap
from pathlib import Path
from typing import Iterable, Iterator, Sequence

Number = int | float

@dataclass(slots=True)
class Tensor:
    shape: tuple[int, ...]
    data: list[float]

    def __post_init__(self) -> None:
        if not self.shape or any(d < 0 for d in self.shape):
            raise ValueError("shape must contain non-negative dimensions")
        expected = 1
        for dimension in self.shape:
            expected *= dimension
        if expected != len(self.data):
            raise ValueError(f"shape {self.shape} requires {expected} values, got {len(self.data)}")

    @classmethod
    def zeros(cls, shape: Sequence[int]) -> "Tensor":
        normalized = tuple(int(d) for d in shape)
        size = 1
        for dimension in normalized: size *= dimension
        return cls(normalized, [0.0] * size)

    @classmethod
    def filled(cls, shape: Sequence[int], value: Number) -> "Tensor":
        result = cls.zeros(shape)
        result.data = [float(value)] * len(result.data)
        return result

    @classmethod
    def from_nested(cls, values: Sequence[object]) -> "Tensor":
        def flatten(value: object, dims: list[int], depth: int = 0) -> list[float]:
            if isinstance(value, (list, tuple)):
                if len(dims) <= depth: dims.append(len(value))
                elif dims[depth] != len(value): raise ValueError("ragged nested data")
                result: list[float] = []
                for item in value: result.extend(flatten(item, dims, depth + 1))
                return result
            return [float(value)]
        dims: list[int] = []
        data = flatten(values, dims)
        return cls(tuple(dims or [1]), data)

    def clone(self) -> "Tensor": return Tensor(self.shape, self.data.copy())
    def __len__(self) -> int: return self.shape[0]

    def _offset(self, indices: Sequence[int]) -> int:
        if len(indices) != len(self.shape): raise IndexError("wrong rank")
        offset = 0
        for index, dimension in zip(indices, self.shape):
            if not 0 <= index < dimension: raise IndexError("index out of bounds")
            offset = offset * dimension + index
        return offset

    def get(self, *indices: int) -> float: return self.data[self._offset(indices)]
    def set(self, indices: Sequence[int], value: Number) -> None: self.data[self._offset(indices)] = float(value)
    def row(self, index: int) -> list[float]:
        if len(self.shape) != 2: raise ValueError("row requires a matrix")
        start = index * self.shape[1]
        return self.data[start:start + self.shape[1]]
    def map(self, function) -> "Tensor": return Tensor(self.shape, [float(function(x)) for x in self.data])
    def add(self, other: "Tensor") -> "Tensor":
        if self.shape != other.shape: raise ValueError("shape mismatch")
        return Tensor(self.shape, [a + b for a, b in zip(self.data, other.data)])
    def scale(self, factor: Number) -> "Tensor": return Tensor(self.shape, [x * float(factor) for x in self.data])

    def reshape(self, shape: Sequence[int]) -> "Tensor":
        normalized = tuple(int(d) for d in shape)
        return Tensor(normalized, self.data.copy())

    def transpose(self) -> "Tensor":
        if len(self.shape) != 2: raise ValueError("transpose currently supports matrices")
        rows, columns = self.shape
        return Tensor((columns, rows), [self.data[row * columns + column] for column in range(columns) for row in range(rows)])

    def matmul(self, other: "Tensor") -> "Tensor":
        if len(self.shape) != 2 or len(other.shape) != 2 or self.shape[1] != other.shape[0]: raise ValueError("matrix shape mismatch")
        rows, inner, columns = self.shape[0], self.shape[1], other.shape[1]
        output = [0.0] * (rows * columns)
        for row in range(rows):
            left = row * inner
            out = row * columns
            for pivot in range(inner):
                coefficient = self.data[left + pivot]
                right = pivot * columns
                for column in range(columns): output[out + column] += coefficient * other.data[right + column]
        return Tensor((rows, columns), output)

    def softmax(self, axis: int = -1) -> "Tensor":
        if axis not in (-1, len(self.shape) - 1): raise ValueError("only final-axis softmax is supported")
        width = self.shape[-1]
        output: list[float] = []
        for start in range(0, len(self.data), width):
            row = self.data[start:start + width]
            maximum = max(row) if row else 0.0
            values = [exp(max(-80.0, min(80.0, x - maximum))) for x in row]
            total = sum(values) or 1.0
            output.extend(value / total for value in values)
        return Tensor(self.shape, output)

    def l2_normalize_rows(self, epsilon: float = 1e-12) -> "Tensor":
        if len(self.shape) != 2: raise ValueError("row normalization requires a matrix")
        width = self.shape[1]; output = self.data.copy()
        for start in range(0, len(output), width):
            norm = sqrt(sum(x * x for x in output[start:start + width]) + epsilon)
            for index in range(start, start + width): output[index] /= norm
        return Tensor(self.shape, output)

class MappedFloat32:
    """Read-only float32 storage backed by an mmap without loading the file."""
    def __init__(self, path: str | Path, offset: int, count: int) -> None:
        import struct
        self.path = Path(path); self.offset = offset; self.count = count; self._struct = struct.Struct("<f")
        self._file = self.path.open("rb"); self._mapping = mmap(self._file.fileno(), 0, access=1)
    def __len__(self) -> int: return self.count
    def __getitem__(self, index: int) -> float:
        if not 0 <= index < self.count: raise IndexError(index)
        return self._struct.unpack_from(self._mapping, self.offset + index * 4)[0]
    def __iter__(self) -> Iterator[float]:
        for index in range(self.count): yield self[index]
    def close(self) -> None: self._mapping.close(); self._file.close()
    def __enter__(self) -> "MappedFloat32": return self
    def __exit__(self, *_: object) -> None: self.close()

def dot(left: Sequence[Number], right: Sequence[Number]) -> float:
    if len(left) != len(right): raise ValueError("vector shape mismatch")
    return sum(float(a) * float(b) for a, b in zip(left, right))

def cosine_similarity(left: Sequence[Number], right: Sequence[Number]) -> float:
    denominator = sqrt(dot(left, left) * dot(right, right))
    return dot(left, right) / denominator if denominator else 0.0

def rms(values: Sequence[Number], epsilon: float = 1e-6) -> float:
    return sqrt(sum(float(value) ** 2 for value in values) / max(1, len(values)) + epsilon)
