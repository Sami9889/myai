from __future__ import annotations
import argparse
from agent_runtime.orchestrator import Orchestrator
from tools.file_reader import FileReader
from tools.file_writer import FileWriter
from tools.file_patcher import FilePatcher
from tools.dir_walker import DirWalker
from tools.linter_bridge import LinterBridge
from tools.system_diagnostics import SystemDiagnostics
from cli_interface.renderer import Renderer
from cli_interface.keybindings import KeyBindings

def build_agent(workspace:str='.'):
    agent=Orchestrator();
    for tool in [FileReader(workspace),FileWriter(workspace),FilePatcher(workspace),DirWalker(workspace),LinterBridge(),SystemDiagnostics()]: agent.register(tool)
    return agent

def run_command(agent, renderer: Renderer, command: str, arguments: list[str]) -> int:
    if command == 'diagnostics':
        result = agent.tools['diagnostics'].run({})
    elif command == 'walk':
        result = agent.tools['walk'].run({'pattern': arguments[0] if arguments else '*'})
    elif command == 'read':
        if not arguments:
            print(renderer.error('Usage: myai read PATH'))
            return 2
        result = agent.tools['read_file'].run({'path': arguments[0]})
    elif command == 'lint':
        if not arguments:
            print(renderer.error('Usage: myai lint PATH'))
            return 2
        result = agent.tools['lint'].run({'path': arguments[0]})
    else:
        return -1
    if result.ok:
        print(renderer.agent(result.output))
        return 0
    print(renderer.error(result.error or result.output or 'command failed'))
    return 1

def main(argv=None)->int:
    parser=argparse.ArgumentParser(prog='myai')
    parser.add_argument('--version', action='version', version='myai 0.1.0')
    parser.add_argument('--workspace',default='.')
    parser.add_argument('task',nargs='*')
    args=parser.parse_args(argv)
    agent=build_agent(args.workspace); renderer=Renderer(); keys=KeyBindings()
    if args.task:
        command = args.task[0]
        command_result = run_command(agent, renderer, command, args.task[1:])
        if command_result >= 0:
            return command_result
        response=agent.run(' '.join(args.task)); print(renderer.agent(response.text)); return 0 if response.state.errors==[] else 1
    print(renderer.paint('myai local agent. /quit exits; /multiline toggles collection.',renderer.BOLD))
    while True:
        try: line=input('you> ')
        except (EOFError,KeyboardInterrupt): print(); return 0
        action=keys.handle(line)
        if action=='quit': return 0
        if action=='multiline': print('multiline='+str(keys.multiline)); continue
        if not line.strip(): continue
        words=line.split()
        command_result=run_command(agent, renderer, words[0], words[1:])
        if command_result >= 0: continue
        response=agent.run(line); print(renderer.agent(response.text))
if __name__=='__main__': raise SystemExit(main())
