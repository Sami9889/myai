from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from time import time
class SessionStatus(str,Enum): IDLE='idle'; THINKING='thinking'; TOOL='tool'; COMPLETE='complete'; FAILED='failed'
@dataclass(slots=True)
class SessionState:
    status: SessionStatus=SessionStatus.IDLE; step:int=0; task:str=''; events:list[str]=field(default_factory=list); errors:list[str]=field(default_factory=list); started:float=field(default_factory=time)
    def transition(self,status:SessionStatus,message:str='') -> None:
        self.status=status; self.step+=1
        if message: self.events.append(message)
    def fail(self,message:str) -> None: self.errors.append(message); self.transition(SessionStatus.FAILED,message)
    def snapshot(self) -> dict[str,object]: return {'status':self.status.value,'step':self.step,'task':self.task,'events':len(self.events),'errors':len(self.errors),'age_seconds':time()-self.started}
