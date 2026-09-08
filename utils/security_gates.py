from __future__ import annotations
import re
from dataclasses import dataclass
from .exceptions import SecurityError

@dataclass(frozen=True, slots=True)
class GateDecision:
    allowed: bool
    reason: str
    requires_confirmation: bool

DANGEROUS = (re.compile(r'(^|\s)rm\s+(-[^ ]*\s+)*-r'), re.compile(r'git\s+push\s+[^\n]*--force'), re.compile(r'(^|\s)mkfs(\s|$)'), re.compile(r'(^|\s)dd\s+'))

def inspect_command(command: str) -> GateDecision:
    for pattern in DANGEROUS:
        if pattern.search(command): return GateDecision(False, 'dangerous command requires explicit confirmation', True)
    if re.search(r'\b(curl|wget|nc|netcat)\b', command): return GateDecision(False, 'network-capable commands are disabled by default', True)
    return GateDecision(True, 'command is within the default policy', False)

def require_confirmation(command: str, confirmer) -> None:
    decision = inspect_command(command)
    if decision.requires_confirmation and not confirmer(command, decision.reason): raise SecurityError('operation rejected by confirmation gate')
    if not decision.allowed and not decision.requires_confirmation: raise SecurityError(decision.reason)
