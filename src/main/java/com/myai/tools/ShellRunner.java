package com.myai.tools;

import com.myai.utils.SecurityGates;

import java.util.Map;
import java.nio.file.Path;
import java.util.function.BiFunction;

public class ShellRunner extends BaseTool {
    public String name() { return "shell"; }
    public String description() { return "Run a non-network shell command after policy confirmation."; }

    private Path workspace;
    private BiFunction<String, String, Boolean> confirmer;

    public ShellRunner(String workspace, BiFunction<String, String, Boolean> confirmer) {
        this.workspace = Path.of(workspace).toAbsolutePath().normalize();
        this.confirmer = confirmer != null ? confirmer : (cmd, reason) -> false;
    }

    @Override
    public Map<String, Object> validate(Map<String, Object> arguments) {
        String command = string(arguments, "command", null);
        double timeout = arguments.containsKey("timeout") ? ((Number) arguments.get("timeout")).doubleValue() : 30.0;
        if (timeout <= 0 || timeout > 300) throw new IllegalArgumentException("timeout must be between 0 and 300 seconds");
        return Map.of("command", command, "timeout", timeout);
    }

    @Override
    public ToolResult execute(Map<String, Object> arguments) throws Exception {
        String command = (String) arguments.get("command");
        double timeout = (Double) arguments.get("timeout");
        SecurityGates.requireConfirmation(command, confirmer);
        ProcessBuilder pb = new ProcessBuilder("sh", "-c", command);
        pb.directory(workspace.toFile());
        pb.redirectErrorStream(true);
        Process process = pb.start();
        StringBuilder output = new StringBuilder();
        try (var reader = new java.io.BufferedReader(new java.io.InputStreamReader(process.getInputStream()))) {
            String line;
            while ((line = reader.readLine()) != null) {
                output.append(line).append("\n");
            }
        }
        boolean finished = process.waitFor((long) timeout, java.util.concurrent.TimeUnit.SECONDS);
        if (!finished) {
            process.destroyForcibly();
            return new ToolResult(false, "", "command timed out");
        }
        int exitCode = process.exitValue();
        String out = output.toString().trim();
        return new ToolResult(exitCode == 0, out, exitCode == 0 ? null : "exit code " + exitCode);
    }
}
