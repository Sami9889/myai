from __future__ import annotations
import os, textwrap
class Renderer:
    RESET='\033[0m'; BOLD='\033[1m'; CYAN='\033[36m'; GREEN='\033[32m'; YELLOW='\033[33m'; RED='\033[31m'; DIM='\033[2m'
    def __init__(self,colour:bool|None=None)->None: self.colour=(os.getenv('NO_COLOR') is None) if colour is None else colour
    def paint(self,text:str,code:str)->str:return code+text+self.RESET if self.colour else text
    def panel(self,title:str,body:str,width:int=78)->str:
        inner=max(10,width-4); lines=[]
        for line in body.splitlines() or ['']: lines.extend(textwrap.wrap(line,inner) or [''])
        border='+'+'-'*(width-2)+'+'; return '\n'.join([border,'| '+title[:inner].ljust(inner)+' |']+['| '+line.ljust(inner)+' |' for line in lines]+[border])
    def user(self,text:str)->str:return self.panel(self.paint(' user ',self.CYAN),text)
    def agent(self,text:str)->str:return self.panel(self.paint(' agent ',self.GREEN),text)
    def error(self,text:str)->str:return self.panel(self.paint(' error ',self.RED),text)
