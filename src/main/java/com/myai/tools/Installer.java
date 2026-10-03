package com.myai.tools;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

public class Installer extends BaseTool {
    public String name() { return "install"; }
    public String description() { return "Install the current repository into its local environment."; }

    private Path workspace;

    public Installer(String workspace) {
        this.workspace = Path.of(workspace).toAbsolutePath().normalize();
    }

    @Override
    public Map<String, Object> validate(Map<String, Object> arguments) {
        Object value = arguments.getOrDefault("confirm", false);
        if (!(value instanceof Boolean confirm)) throw new IllegalArgumentException("confirm must be boolean");
        return Map.of("confirm", confirm);
    }

    @Override
    public ToolResult execute(Map<String, Object> arguments) throws Exception {
        boolean confirm = (Boolean) arguments.get("confirm");
        if (!confirm) return new ToolResult(false, "", "installation requires explicit confirmation");
        Path script = workspace.resolve("install.sh");
        if (!Files.exists(script)) return new ToolResult(false, "", "install.sh was not found");
        ProcessBuilder pb = new ProcessBuilder("bash", script.toString());
        pb.directory(workspace.toFile());
        pb.redirectErrorStream(true);
        Process process = pb.start();
        StringBuilder output = new StringBuilder();
        try (var reader = new java.io.BufferedReader(new java.io.InputStreamReader(process.getInputStream()))) {
            String line;
            while ((line = reader.readLine()) != null) output.append(line).append("\n");
        }
        int exitCode = process.waitFor();
        return new ToolResult(exitCode == 0, output.toString().trim(), exitCode == 0 ? null : "installer exited with " + exitCode);
    }
}
