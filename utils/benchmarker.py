from __future__ import annotations
from dataclasses import dataclass
from time import perf_counter
from typing import Callable, Any
@dataclass(frozen=True,slots=True)
class Benchmark:
    name:str; seconds:float; result:Any

def measure(name:str,function:Callable[[],Any])->Benchmark:
    start=perf_counter(); result=function(); return Benchmark(name,perf_counter()-start,result)
