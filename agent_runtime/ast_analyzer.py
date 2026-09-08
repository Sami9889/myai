from __future__ import annotations
import ast
from pathlib import Path
class ASTAnalyzer:
    def parse(self,source:str,filename:str='<memory>')->ast.AST: return ast.parse(source,filename)
    def symbols(self,source:str)->list[dict[str,object]]:
        tree=self.parse(source); results=[]
        for node in ast.walk(tree):
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)): results.append({'name':node.name,'kind':type(node).__name__,'line':node.lineno,'end_line':getattr(node,'end_lineno',node.lineno)})
        return sorted(results,key=lambda item:int(item['line']))
    def imports(self,source:str)->list[str]:
        return [node.names[0].name for node in ast.walk(self.parse(source)) if isinstance(node,(ast.Import,ast.ImportFrom)) and node.names]
    def validate_file(self,path:str|Path)->list[str]:
        try: self.parse(Path(path).read_text(encoding='utf-8'),str(path)); return []
        except SyntaxError as exc: return [f'{exc.lineno}:{exc.offset}: {exc.msg}']
