---
name: performance
description: "Use when profiling or optimizing tensor math, attention, tokenization, memory retrieval, file indexing, or CLI startup."
---

Optimize only from measurements.

Capture a focused baseline, identify the dominant operation, preserve numerical and security behavior, and compare after the change. Prefer fewer allocations, bounded scans, mmap where appropriate, and clear resource ownership. Do not add opaque native dependencies or premature caches. Report workload, timing, memory assumptions, and any tradeoff.
