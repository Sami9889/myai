package com.myai.cli;

import com.myai.agent.runtime.AgentConfig;
import com.myai.agent.runtime.AgentResponse;
import com.myai.agent.runtime.Orchestrator;
import com.myai.agent.runtime.TaskList;
import com.myai.cli.Highlighter;
import com.myai.cli.Intent;
import com.myai.cli.KeyBindings;
import com.myai.cli.Renderer;
import com.myai.cli.Spinner;
import com.myai.tools.BaseTool;
import com.myai.tools.CodeExecutor;
import com.myai.tools.DirWalker;
import com.myai.tools.FilePatcher;
import com.myai.tools.FileReader;
import com.myai.tools.FileWriter;
import com.myai.tools.HelpSearch;
import com.myai.tools.Installer;
import com.myai.tools.LinterBridge;
import com.myai.tools.RepoManager;
import com.myai.tools.ShellRunner;
import com.myai.tools.SystemDiagnostics;
import com.myai.tools.ToolResult;
import com.myai.tools.WebReader;
import com.myai.tools.WebSearch;
import com.myai.utils.ConfigLoader;

public class Repl {
    private static final String VERSION = "myai 0.1.0";

    public static void main(String[] args) throws Exception {
        Map<String, Object> parsedArgs = parseArgs(args);
        String workspace = (String) parsedArgs.getOrDefault("workspace", ".");
        Path workspacePath = Path.of(workspace).toAbsolutePath().normalize();
        List<String> task = (List<String>) parsedArgs.get("task");

        Renderer renderer = new Renderer();
        KeyBindings keys = new KeyBindings();
        TaskList tasks = new TaskList(workspace);

        Map<String, BaseTool> tools = new LinkedHashMap<>();
        tools.put("read_file", new FileReader(workspace));
        tools.put("write_file", new FileWriter(workspace));
        tools.put("patch_file", new FilePatcher(workspace));
        tools.put("walk", new DirWalker(workspace));
        tools.put("lint", new LinterBridge());
        tools.put("diagnostics", new SystemDiagnostics());
        tools.put("search", new HelpSearch(workspace));
        tools.put("repo", new RepoManager(workspace));
        tools.put("install", new Installer(workspace));
        tools.put("shell", new ShellRunner(workspace, (cmd, reason) -> {
            System.out.println(renderer.activity("confirm", cmd + " (" + reason + ")"));
            return false;
        }));

        AgentConfig config = new AgentConfig();
        Orchestrator agent = new Orchestrator(null, tools, config);

        if (task != null && !task.isEmpty()) {
            String commandStr = String.join(" ", task);
            int result = runRequest(agent, renderer, commandStr, tasks);
            if (result >= 0) {
                System.exit(result);
            }
            System.out.println(renderer.activity("accepted", commandStr));
            AgentResponse response = agent.run(commandStr);
            System.out.println(renderer.activity(response.state().errors().isEmpty() ? "completed" : "failed", "agent response"));
            System.out.println(renderer.agent(response.text()));
            System.exit(response.state().errors().isEmpty() ? 0 : 1);
        }

        System.out.println(renderer.banner());
        System.out.println(renderer.session(workspacePath.toString()));
        System.out.println(renderer.footer());
        System.out.println(renderer.dim("Local tools online. /quit exits; /multiline toggles collection."));

        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));
        String line;
        while ((line = reader.readLine()) != null) {
            String action = keys.handle(line);
            if ("quit".equals(action)) {
                System.out.println();
                System.exit(0);
            }
            if ("multiline".equals(action)) {
                System.out.println("multiline=" + keys.multiline());
                continue;
            }
            if (line.isBlank()) continue;
            int cmdResult = runRequest(agent, renderer, line, tasks);
            if (cmdResult >= 0) continue;
            System.out.println(renderer.activity("accepted", line));
            AgentResponse response = agent.run(line);
            System.out.println(renderer.activity(response.state().errors().isEmpty() ? "completed" : "failed", "agent response"));
            System.out.println(renderer.agent(response.text()));
        }
        System.out.println();
        System.exit(0);
    }

    private static int runRequest(Orchestrator agent, Renderer renderer, String text, TaskList tasks) {
        Intent intent = Intent.parseIntent(text);
        if (intent != null) {
            System.out.println(renderer.activity("understood", intent.explanation()));
            return runCommand(agent, renderer, intent.command(), intent.arguments(), tasks);
        }
        String[] words = text.split("\\s+");
        if (words.length == 0) return -1;
        int result = runCommand(agent, renderer, words[0], Arrays.asList(words).subList(1, words.length), tasks);
        if (result >= 0) return result;
        return -1;
    }

    private static int runCommand(Orchestrator agent, Renderer renderer, String command, List<String> arguments, TaskList tasks) {
        String detail = command + (arguments.isEmpty() ? "" : " " + String.join(" ", arguments));
        System.out.println(renderer.activity("executing", detail));
        BaseTool tool = agent.tools().get(command);
        if (tool == null) {
            return -1;
        }
        try {
            ToolResult result = switch (command) {
                case "diagnostics" -> agent.tools().get("diagnostics").run(Map.of());
                case "walk" -> agent.tools().get("walk").run(Map.of("pattern", arguments.isEmpty() ? "*" : arguments.get(0)));
                case "read_file" -> {
                    if (arguments.isEmpty()) {
                        System.out.println(renderer.error("Usage: myai read PATH"));
                        yield new ToolResult(false, "", "missing path");
                    }
                    yield agent.tools().get("read_file").run(Map.of("path", arguments.get(0)));
                }
                case "write_file" -> {
                    if (arguments.size() < 2) {
                        System.out.println(renderer.error("Usage: write PATH CONTENT"));
                        yield new ToolResult(false, "", "missing arguments");
                    }
                    yield agent.tools().get("write_file").run(Map.of("path", arguments.get(0), "content", String.join(" ", arguments.subList(1, arguments.size()))));
                }
                case "lint" -> {
                    if (arguments.isEmpty()) {
                        System.out.println(renderer.error("Usage: myai lint PATH"));
                        yield new ToolResult(false, "", "missing path");
                    }
                    yield agent.tools().get("lint").run(Map.of("path", arguments.get(0)));
                }
                case "search" -> {
                    if (arguments.isEmpty()) {
                        System.out.println(renderer.error("Usage: search QUERY"));
                        yield new ToolResult(false, "", "missing query");
                    }
                    yield agent.tools().get("search").run(Map.of("query", String.join(" ", arguments)));
                }
                case "todo" -> {
                    if (arguments.isEmpty() || "list".equals(arguments.get(0))) {
                        System.out.println(renderer.activity("completed", "todo list"));
                        System.out.println(renderer.agent(tasks.render()));
                        yield new ToolResult(true, "", null);
                    }
                    String action = arguments.get(0);
                    yield switch (action) {
                        case "add" -> {
                            TaskList.TaskItem item = tasks.add(String.join(" ", arguments.subList(1, arguments.size())));
                            System.out.println(renderer.agent("Added task " + item.id() + ": " + item.title()));
                            yield new ToolResult(true, "", null);
                        }
                        case "done" -> {
                            if (arguments.size() < 2) {
                                yield new ToolResult(false, "", "missing task id");
                            }
                            TaskList.TaskItem item = tasks.complete(Integer.parseInt(arguments.get(1)));
                            System.out.println(renderer.agent("Completed task " + item.id() + ": " + item.title()));
                            yield new ToolResult(true, "", null);
                        }
                        case "clear" -> {
                            int cleared = tasks.clearCompleted();
                            System.out.println(renderer.agent("Cleared " + cleared + " completed task(s)."));
                            yield new ToolResult(true, "", null);
                        }
                        default -> new ToolResult(false, "", "Usage: todo add TITLE | todo list | todo done ID | todo clear");
                    };
                }
                case "time" -> {
                    System.out.println(renderer.activity("completed", "time"));
                    System.out.println(renderer.agent(java.time.Instant.now().toString()));
                    yield new ToolResult(true, "", null);
                }
                case "status" -> {
                    System.out.println(renderer.activity("completed", "status"));
                    System.out.println(renderer.agent(agent.snapshot().toString()));
                    yield new ToolResult(true, "", null);
                }
                case "help" -> {
                    System.out.println(renderer.activity("completed", "help"));
                    System.out.println(renderer.agent("You can type naturally: \"read README.md\", \"show Python files\", \"add a task to review code\", \"search help for tokenizer\", or \"install this repo yes\". Exact commands: diagnostics, walk, read, write, lint, search, todo, repo, install, time, status, /quit."));
                    yield new ToolResult(true, "", null);
                }
                case "install" -> agent.tools().get("install").run(Map.of("confirm", arguments.contains("--confirm")));
                case "repo" -> {
                    String op = arguments.isEmpty() ? "status" : arguments.get(0);
                    boolean confirm = arguments.contains("--confirm");
                    List<String> values = new ArrayList<>();
                    for (String v : arguments.subList(1, arguments.size())) {
                        if (!"--confirm".equals(v)) values.add(v);
                    }
                    Map<String, Object> payload = new LinkedHashMap<>();
                    payload.put("operation", op);
                    payload.put("confirm", confirm);
                    if ("commit".equals(op)) payload.put("message", String.join(" ", values));
                    else if ("add".equals(op)) payload.put("paths", values);
                    yield agent.tools().get("repo").run(payload);
                }
                default -> new ToolResult(false, "", "unknown command: " + command);
            };

            if (result.ok()) {
                System.out.println(renderer.activity("completed", command));
                System.out.println(renderer.agent(result.output()));
                return 0;
            }
            System.out.println(renderer.activity("failed", command));
            System.out.println(renderer.error(result.error() != null ? result.error() : result.output()));
            return 1;
        } catch (Exception e) {
            System.out.println(renderer.activity("failed", command));
            System.out.println(renderer.error(e.getMessage()));
            return 1;
        }
    }

    private static Map<String, Object> parseArgs(String[] args) {
        Map<String, Object> result = new LinkedHashMap<>();
        List<String> task = new ArrayList<>();
        for (int i = 0; i < args.length; i++) {
            if ("--workspace".equals(args[i]) && i + 1 < args.length) {
                result.put("workspace", args[++i]);
            } else {
                task.add(args[i]);
            }
        }
        result.put("task", task);
        return result;
    }
}
