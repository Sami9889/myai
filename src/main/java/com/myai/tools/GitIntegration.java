package com.myai.tools;

import java.util.Map;

public class GitIntegration extends BaseTool {
    public String name() { return "git"; }
    public String description() { return "Inspect git state with safe read-only operations." }

    private final ShellRunner runner;

    public GitIntegration(String workspace) {
        this.runner = new ShellRunner(workspace, (cmd, reason) -> true);
    }

    @Override
    public Map<String, Object> validate(Map<String, Object> arguments) {
        String operation = string(arguments, "operation", null);
        if (!Set.of("status", "diff", "log", "branch").contains(operation))
            throw new IllegalArgumentException("operation is not read-only or supported");
        return Map.of("operation", operation);
    }

    @Override
    public ToolResult execute(Map<String, Object> arguments) throws Exception {
        String operation = (String) arguments.get("operation");
        Map<String, Object> cmd = Map.of("command", "git " + operation);
        return runner.run(cmd);
    }
}
