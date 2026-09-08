"""Bounded local agent loop with explicit tool calls and loop recovery."""
from __future__ import annotations
from dataclasses import dataclass, field
import json, re
from typing import Callable, Any
from .state_machine import SessionState, SessionStatus
from .context_compressor import ContextCompressor
from utils.logger import get_logger
from tools.base_tool import BaseTool, ToolResult
from .conversation import local_reply

@dataclass(slots=True)
class AgentConfig:
    max_steps:int=32
    max_context_tokens:int=2048
    max_repeated_actions:int=3

@dataclass(slots=True)
class AgentResponse:
    text:str
    state:SessionState
    tool_results:list[ToolResult]=field(default_factory=list)

class Orchestrator:
    """Coordinates model generation, structured tool calls, context, reflection, and recovery.

    The model callback receives a list of role/content dictionaries and returns text. Keeping
    this boundary as a callback allows a raw custom transformer to be supplied without coupling
    orchestration to a particular weight layout.
    """
    TOOL_PATTERN=re.compile(r'<tool\s+name=["\'](?P<name>[\w.-]+)["\']\s*>(?P<body>.*?)</tool>',re.S|re.I)
    JSON_PATTERN=re.compile(r'```tool\s*(?P<body>\{.*?\})\s*```',re.S|re.I)
    def __init__(self, model:Callable[[list[dict[str,str]]],str]|None=None, tools:dict[str,BaseTool]|None=None, config:AgentConfig|None=None, logger=None)->None:
        self.model=model; self.tools=tools or {}; self.config=config or AgentConfig(); self.logger=logger or get_logger(); self.compressor=ContextCompressor(self.config.max_context_tokens); self.messages:list[dict[str,str]]=[]; self.state=SessionState()
    def register(self,tool:BaseTool)->None: self.tools[tool.name]=tool
    def _parse_calls(self,text:str)->list[tuple[str,dict[str,Any]]]:
        calls=[]
        for match in self.TOOL_PATTERN.finditer(text):
            body=match.group('body').strip()
            try: arguments=json.loads(body)
            except json.JSONDecodeError: arguments={'input':body}
            if isinstance(arguments,dict): calls.append((match.group('name'),arguments))
        for match in self.JSON_PATTERN.finditer(text):
            try:
                payload=json.loads(match.group('body')); name=payload.pop('name'); calls.append((name,payload))
            except (json.JSONDecodeError,KeyError,TypeError): continue
        return calls
    def _invoke(self,name:str,arguments:dict[str,Any])->ToolResult:
        tool=self.tools.get(name)
        if tool is None: return ToolResult(False,'',f'unknown tool: {name}')
        self.state.transition(SessionStatus.TOOL,f'tool:{name}')
        result=tool.run(arguments)
        self.messages.append({'role':'tool','content':json.dumps({'name':name,'ok':result.ok,'output':result.output,'error':result.error})})
        return result
    def _fallback(self,task:str)->str:
        conversational = local_reply(task)
        if conversational is not None:
            return conversational
        return (
            'Task received: ' + task + '\n\n'
            'Neural generation is unavailable because config.json has no local '
            'model path configured. The CLI is online and its deterministic '
            'workspace tools are ready. Try `diagnostics`, `walk *.py`, '
            '`read README.md`, or `lint PATH`.'
        )
    def _reflect(self,task:str,answer:str,results:list[ToolResult])->str:
        failures=sum(not item.ok for item in results)
        if failures: return f'{answer}\n\nRecovery: {failures} tool operation(s) failed; inspect the reported errors before retrying.'
        return answer
    def run(self,task:str)->AgentResponse:
        self.state=SessionState(task=task); self.messages=[{'role':'system','content':'You are a local-only agent. Use <tool name="name">{json}</tool> for tools.'},{'role':'user','content':task}]; results=[]; seen:dict[str,int]={}; answer=''
        for _ in range(max(1,self.config.max_steps)):
            self.state.transition(SessionStatus.THINKING)
            context=self.compressor.compress(self.messages)
            generated=self.model(context) if self.model else self._fallback(task)
            calls=self._parse_calls(generated)
            if not calls:
                answer=generated; self.messages.append({'role':'assistant','content':generated}); self.state.transition(SessionStatus.COMPLETE); return AgentResponse(self._reflect(task,answer,results),self.state,results)
            action_key=json.dumps(calls,sort_keys=True)
            seen[action_key]=seen.get(action_key,0)+1
            if seen[action_key]>self.config.max_repeated_actions:
                answer='The same tool request repeated too many times; execution stopped for safety.'; self.state.fail(answer); return AgentResponse(answer,self.state,results)
            self.messages.append({'role':'assistant','content':generated})
            for name,arguments in calls: results.append(self._invoke(name,arguments))
        answer='Maximum agent steps reached without a final response.'; self.state.fail(answer); return AgentResponse(answer,self.state,results)
    def reset(self)->None: self.messages.clear(); self.state=SessionState()
    def snapshot(self)->dict[str,object]: return {'state':self.state.snapshot(),'messages':len(self.messages),'tools':sorted(self.tools)}
