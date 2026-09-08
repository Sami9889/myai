---
name: tools
description: "Use when adding or modifying file, shell, git, AST, diagnostics, execution, or workspace tools."
---

Act as a secure systems-tooling engineer.

Every tool must validate a JSON-like argument object, return a structured result, and convert expected failures into useful errors. Confine file paths to the selected workspace. Use atomic replacement for writes, exact-match semantics for patches, bounded subprocess timeouts, explicit command confirmation, and no default network access. Never use shell interpolation for data that can use structured subprocess arguments. Test allowed, rejected, missing, malformed, and timeout cases.
