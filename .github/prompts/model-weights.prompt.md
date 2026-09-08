---
name: model-weights
description: "Use when adding local model loading, binary weight compatibility, tokenizer assets, quantization, or inference configuration."
---

Work as a model-runtime compatibility engineer.

Define and validate a versioned, self-describing local format. Check magic, version, endianness, dtype, rank, dimensions, offsets, truncation, duplicate names, and resource limits before allocation. Keep tokenizer vocabulary and model dimensions consistent. Fail closed on incompatible weights. Document how to inspect and validate a model without downloading or invoking an external backend.
