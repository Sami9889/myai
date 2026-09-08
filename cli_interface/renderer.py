from __future__ import annotations
import os, textwrap
from datetime import datetime, timezone
class Renderer:
    RESET='\033[0m'; BOLD='\033[1m'; CYAN='\033[36m'; GREEN='\033[32m'; YELLOW='\033[33m'; RED='\033[31m'; DIM='\033[2m'
    def __init__(self,colour:bool|None=None)->None: self.colour=(os.getenv('NO_COLOR') is None) if colour is None else colour
    def paint(self,text:str,code:str)->str:return code+text+self.RESET if self.colour else text
    def panel(self,title:str,body:str,width:int|None=None)->str:
        width=width or min(96,max(56,os.get_terminal_size().columns if os.isatty(1) else 78))
        inner=max(10,width-4); lines=[]
        for line in body.splitlines() or ['']: lines.extend(textwrap.wrap(line,inner) or [''])
        border=self.paint('+'+'='*(width-2)+'+',self.CYAN)
        heading=self.paint('| '+title[:inner].ljust(inner)+' |',self.BOLD)
        content=['| '+line.ljust(inner)+' |' for line in lines]
        return '\n'.join([border,heading]+content+[border])
    def banner(self)->str:
        return self.paint('myai :: LOCAL CODING AGENT',self.BOLD+'\033[36m')
    def session(self,workspace:str)->str:
        timestamp=datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')
        return self.paint(f'workspace={workspace} | mode=offline | started={timestamp}',self.DIM)
    def activity(self,phase:str,detail:str)->str:
        timestamp=datetime.now(timezone.utc).astimezone().strftime('%H:%M:%S')
        label=f'[{timestamp}] {phase.upper():<10}'
        return self.paint(label,self.YELLOW)+' '+detail
    def footer(self)->str:
        return self.paint('------------------------------------------------------------',self.DIM)
    def prompt(self)->str:
        return self.paint('you> ',self.BOLD+'\033[36m')
    def user(self,text:str)->str:return self.panel(self.paint(' user ',self.CYAN),text)
    def agent(self,text:str)->str:return self.panel(self.paint(' agent ',self.GREEN),text)
    def error(self,text:str)->str:return self.panel(self.paint(' error ',self.RED),text)
