---
name: debug
description: "Use when diagnosing a failing CLI command, Pylance diagnostic, import problem, runtime exception, or unexpected agent behavior."
---

Debug from evidence.

Reproduce the exact command or diagnostic first. Capture interpreter path, working directory, inputs, exception, and relevant state. Separate environment, packaging, import, control-flow, and data-shape hypotheses. Make one minimal fix at the controlling boundary, then rerun the same failing check. Do not mask errors with broad exception handling or editor-only configuration unless the diagnostic is proven to be editor-only.
