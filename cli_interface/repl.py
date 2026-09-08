from __future__ import annotations
import argparse
from datetime import datetime, timezone
from pathlib import Path
from agent_runtime.orchestrator import Orchestrator
from agent_runtime.task_list import TaskList
from core_engine.model_loader import load_local_model
from tools.file_reader import FileReader
from tools.file_writer import FileWriter
from tools.file_patcher import FilePatcher
from tools.dir_walker import DirWalker
from tools.linter_bridge import LinterBridge
from tools.system_diagnostics import SystemDiagnostics
from tools.help_search import HelpSearch
from tools.repo_manager import RepoManager
from tools.installer import Installer
from utils.config_loader import load_config
from cli_interface.intent import Intent, parse_intent
from cli_interface.renderer import Renderer
from cli_interface.keybindings import KeyBindings

def build_agent(workspace:str='.'):
    config = load_config(Path(workspace) / "config.json")
    model = load_local_model(config)
    agent=Orchestrator(model=model)
    for tool in [FileReader(workspace),FileWriter(workspace),FilePatcher(workspace),DirWalker(workspace),LinterBridge(),SystemDiagnostics(),HelpSearch(workspace),RepoManager(workspace),Installer(workspace)]: agent.register(tool)
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
        print(renderer.agent('You can type naturally: "read README.md", "show Python files", "add a task to review code", "search help for tokenizer", or "install this repo yes". Exact commands: diagnostics, walk, read, write, lint, search, todo, repo, install, time, status, /quit.'))
        return 0
    elif command == 'install':
        result = agent.tools['install'].run({'confirm': '--confirm' in arguments})
    elif command == 'repo':
        operation = arguments[0] if arguments else 'status'
        confirm = '--confirm' in arguments
        values = [value for value in arguments[1:] if value != '--confirm']
        payload = {'operation': operation, 'confirm': confirm}
        if operation == 'commit':
            payload['message'] = ' '.join(values)
        elif operation == 'add':
            payload['paths'] = values
        result = agent.tools['repo'].run(payload)
    else:
        return -1
    if result.ok:
        print(renderer.activity('completed', command))
        print(renderer.agent(result.output))
        return 0
    print(renderer.activity('failed', command))
    print(renderer.error(result.error or result.output or 'command failed'))
    return 1

def run_request(agent, renderer: Renderer, text: str, tasks: TaskList) -> int:
    intent = parse_intent(text)
    if intent is not None:
        print(renderer.activity('understood', intent.explanation))
        return run_command(agent, renderer, intent.command, intent.arguments, tasks)
    words = text.split()
    command_result = run_command(agent, renderer, words[0], words[1:], tasks) if words else -1
    if command_result >= 0:
        return command_result
    return -1

def main(argv=None)->int:
    parser=argparse.ArgumentParser(prog='myai')
    parser.add_argument('--version', action='version', version='myai 0.1.0')
    parser.add_argument('--workspace',default='.')
    parser.add_argument('task',nargs='*')
    args=parser.parse_args(argv)
    agent=build_agent(args.workspace); renderer=Renderer(); keys=KeyBindings(); tasks=TaskList(args.workspace)
    if args.task:
        command = args.task[0]
        command_result = run_request(agent, renderer, ' '.join(args.task), tasks)
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
        command_result=run_request(agent, renderer, line, tasks)
        if command_result >= 0: continue
        print(renderer.activity('accepted', line))
        response=agent.run(line)
        print(renderer.activity('completed' if not response.state.errors else 'failed', 'agent response'))
        print(renderer.agent(response.text))
if __name__=='__main__': raise SystemExit(main())
