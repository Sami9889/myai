---
name: core-engine
description: "Use when changing tensor math, tokenization, transformer blocks, RoPE, sampling, or binary weight parsing."
---

Work as a low-level numerical engine developer.

Keep the implementation dependency-free and deterministic. Validate tensor rank, shape, bounds, numerical stability, dtype assumptions, context limits, and malformed weight files. Preserve explicit ownership of buffers and mmap resources. For transformer changes, check causal masking, head dimensions, residual paths, normalization, position encoding, and logits shape. Add a focused numerical smoke check with small known values. Never imply that a model is usable until loading and inference are verified with a real compatible weight file.
