---
name: attention
description: "Use for multi-head attention, causal masks, RoPE, ALiBi, KV state, and transformer correctness."
---

Check head divisibility, causal visibility, scaling, position behavior, context limits, and residual shapes. Use tiny hand-checkable sequences and compare masked positions. Do not optimize before correctness and memory behavior are measured.
