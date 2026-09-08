from __future__ import annotations
import argparse
from datetime import datetime, timezone
from agent_runtime.orchestrator import Orchestrator
from agent_runtime.task_list import TaskList
from tools.file_reader import FileReader
from tools.file_writer import FileWriter
from tools.file_patcher import FilePatcher
from tools.dir_walker import DirWalker
from tools.linter_bridge import LinterBridge
from tools.system_diagnostics import SystemDiagnostics
from tools.help_search import HelpSearch
from cli_interface.renderer import Renderer
from cli_interface.keybindings import KeyBindings

def build_agent(workspace:str='.'):
    agent=Orchestrator();
    for tool in [FileReader(workspace),FileWriter(workspace),FilePatcher(workspace),DirWalker(workspace),LinterBridge(),SystemDiagnostics(),HelpSearch(workspace)]: agent.register(tool)
    return agent

def run_command(agent, renderer: Renderer, command: str, arguments: list[str], tasks: TaskList) -> int:
    detail = ' '.join([command, *arguments]).strip()
    print(renderer.activity('executing', detail))
    if command == 'diagnostics':
        result = agent.tools['diagnostics'].run({})
    elif command == 'walk':
        result = agent.tools['walk'].run({'pattern': arguments[0] if arguments else '*'})
    elif command == 'read':
        if not arguments:
            print(renderer.error('Usage: myai read PATH'))
            return 2
        result = agent.tools['read_file'].run({'path': arguments[0]})
    elif command == 'write':
        if len(arguments) < 2:
            print(renderer.error('Usage: write PATH CONTENT'))
            return 2
        result = agent.tools['write_file'].run({'path': arguments[0], 'content': ' '.join(arguments[1:])})
    elif command == 'lint':
        if not arguments:
            print(renderer.error('Usage: myai lint PATH'))
            return 2
        result = agent.tools['lint'].run({'path': arguments[0]})
    elif command == 'search':
        if not arguments:
            print(renderer.error('Usage: search QUERY'))
            return 2
        result = agent.tools['search'].run({'query': ' '.join(arguments)})
    elif command == 'todo':
        if not arguments or arguments[0] == 'list':
            print(renderer.activity('completed', 'todo list'))
            print(renderer.agent(tasks.render()))
            return 0
        try:
            action = arguments[0]
            if action == 'add':
                item = tasks.add(' '.join(arguments[1:]))
                print(renderer.agent(f'Added task {item.id}: {item.title}'))
            elif action == 'done' and len(arguments) == 2:
                item = tasks.complete(int(arguments[1]))
                print(renderer.agent(f'Completed task {item.id}: {item.title}'))
            elif action == 'clear':
                print(renderer.agent(f'Cleared {tasks.clear_completed()} completed task(s).'))
            else:
                print(renderer.error('Usage: todo add TITLE | todo list | todo done ID | todo clear'))
                return 2
        except (ValueError, OSError) as exc:
            print(renderer.error(str(exc)))
            return 1
        print(renderer.activity('completed', 'todo'))
        return 0
    elif command == 'time':
        print(renderer.activity('completed', 'time'))
        print(renderer.agent(datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')))
        return 0
    elif command == 'status':
        print(renderer.activity('completed', 'status'))
        print(renderer.agent(str(agent.snapshot())))
        return 0
    elif command == 'help':
        print(renderer.activity('completed', 'help'))
        print(renderer.agent('Commands: diagnostics, walk PATTERN, read PATH, write PATH CONTENT, lint PATH, search QUERY, todo add/list/done/clear, time, status, /quit'))
        return 0
    else:
        return -1
    if result.ok:
        print(renderer.activity('completed', command))
        print(renderer.agent(result.output))
        return 0
    print(renderer.activity('failed', command))
    print(renderer.error(result.error or result.output or 'command failed'))
    return 1

def main(argv=None)->int:
    parser=argparse.ArgumentParser(prog='myai')
    parser.add_argument('--version', action='version', version='myai 0.1.0')
    parser.add_argument('--workspace',default='.')
    parser.add_argument('task',nargs='*')
    args=parser.parse_args(argv)
    agent=build_agent(args.workspace); renderer=Renderer(); keys=KeyBindings(); tasks=TaskList(args.workspace)
    if args.task:
        command = args.task[0]
        command_result = run_command(agent, renderer, command, args.task[1:], tasks)
        if command_result >= 0:
            return command_result
        task=' '.join(args.task)
        print(renderer.activity('accepted', task))
        response=agent.run(task)
        print(renderer.activity('completed' if not response.state.errors else 'failed', 'agent response'))
        print(renderer.agent(response.text))
        return 0 if response.state.errors==[] else 1
    print(renderer.banner())
    print(renderer.session(args.workspace))
    print(renderer.footer())
    print(renderer.paint('Local tools online. /quit exits; /multiline toggles collection.',renderer.DIM))
    while True:
        try: line=input(renderer.prompt())
        except (EOFError,KeyboardInterrupt): print(); return 0
        action=keys.handle(line)
        if action=='quit': return 0
        if action=='multiline': print('multiline='+str(keys.multiline)); continue
        if not line.strip(): continue
        words=line.split()
        command_result=run_command(agent, renderer, words[0], words[1:], tasks)
        if command_result >= 0: continue
        print(renderer.activity('accepted', line))
        response=agent.run(line)
        print(renderer.activity('completed' if not response.state.errors else 'failed', 'agent response'))
        print(renderer.agent(response.text))
if __name__=='__main__': raise SystemExit(main())
