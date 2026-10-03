package com.myai.tools;

import java.util.Map;

public class CodeExecutor extends BaseTool {
    public String name() { return "python"; }
    public String description() { return "Execute a Python snippet with timeout and no inherited environment."; }

    private final ShellRunner runner;

    public CodeExecutor(String workspace, java.util.function.BiFunction<String, String, Boolean> confirmer) {
        this.runner = new ShellRunner(workspace, confirmer);
    }

    @Override
    public Map<String, Object> validate(Map<String, Object> arguments) {
        return Map.of("code", string(arguments, "code", null), "timeout", arguments.getOrDefault("timeout", 10));
    }

    @Override
    public ToolResult execute(Map<String, Object> arguments) throws Exception {
        String code = (String) arguments.get("code");
        double timeout = ((Number) arguments.get("timeout")).doubleValue();
        Map<String, Object> cmd = Map.of("command", "python3 -I -c '" + code.replace("'", "'\\''") + "'", "timeout", timeout);
        return runner.run(cmd);
    }
}
