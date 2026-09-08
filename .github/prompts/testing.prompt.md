---
name: testing
description: "Use when designing focused validation, regression checks, smoke tests, benchmarks, or release health checks."
---

Design tests around risk and behavior.

Prefer standard-library tests and executable CLI checks. Cover happy path, malformed input, boundary values, permission/path rejection, subprocess timeout, tool failure, repeated agent actions, no-model fallback, terminal piping, and NO_COLOR. Keep tests deterministic and isolated. Do not reintroduce deleted test artifacts or commit generated virtualenv, cache, egg-info, task, or update-lock files.
