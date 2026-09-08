---
name: refactoring
description: "Use for restructuring code without changing behavior, reducing duplication, or clarifying ownership."
---

Establish behavior with a focused check first. Make one coherent structural change at a time, preserve public APIs, and avoid unrelated formatting. Remove dead paths only when verified unused. Re-run the same behavior check and compare the diff for accidental scope.
