package com.myai.tools;

import com.myai.utils.SecurityGates;
import com.myai.utils.Validators;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

public class RepoManager extends BaseTool {
    public String name() { return "repo"; }
    public String description() { return "Inspect and explicitly publish changes in the current Git repository." }

    private Path workspace;

    public RepoManager(String workspace) {
        this.workspace = Path.of(workspace).toAbsolutePath().normalize();
    }

    @Override
    public Map<String, Object> validate(Map<String, Object> arguments) {
        String operation = string(arguments, "operation", null);
        if (!Set.of("status", "add", "commit", "push").contains(operation))
            throw new IllegalArgumentException("operation must be status, add, commit, or push");
        boolean confirm = (Boolean) arguments.getOrDefault("confirm", false);
        if (!(confirm instanceof Boolean)) throw new IllegalArgumentException("confirm must be boolean");
        Object pathsObj = arguments.get("paths");
        if (!(pathsObj instanceof List<?> paths) || paths.stream().anyMatch(p -> !(p instanceof String)))
            throw new IllegalArgumentException("paths must be a list of strings");
        String message = (String) arguments.getOrDefault("message", "");
        if (!(message instanceof String)) throw new IllegalArgumentException("message must be a string");
        return Map.of("operation", operation, "confirm", confirm, "paths", pathsObj, "message", message);
    }

    @Override
    public ToolResult execute(Map<String, Object> arguments) throws Exception {
        String operation = (String) arguments.get("operation");
        if ("status".equals(operation)) {
            return runGit("status", "--short", "--branch");
        }
        boolean confirm = (Boolean) arguments.get("confirm");
        if (!confirm) return new ToolResult(false, "", operation + " requires explicit --confirm");
        switch (operation) {
            case "add" -> {
                List<String> paths = (List<String>) arguments.get("paths");
                if (paths.isEmpty()) paths = List.of(".");
                List<String> safePaths = new ArrayList<>();
                for (String p : paths) {
                    Path path = Validators.confinedPath(p, workspace.toString());
                    safePaths.add(workspace.relativize(path).toString());
                }
                return runGit("add", "--", String.join(" ", safePaths));
            }
            case "commit" -> {
                String message = ((String) arguments.get("message")).strip();
                if (message.isEmpty()) return new ToolResult(false, "", "commit requires a non-empty message");
                return runGit("commit", "-m", message);
            }
            case "push" -> {
                return runGit("push", "origin", "HEAD");
            }
            default -> {
                return new ToolResult(false, "", "unknown operation: " + operation);
            }
        }
    }

    private ToolResult runGit(String... args) {
        try {
            ProcessBuilder pb = new ProcessBuilder();
            pb.command("git");
            pb.directory(workspace.toFile());
            List<String> cmd = new ArrayList<>(List.of("git"));
            cmd.addAll(List.of(args));
            pb.command(cmd);
            pb.redirectErrorStream(true);
            Process process = pb.start();
            StringBuilder output = new StringBuilder();
            try (var reader = new java.io.BufferedReader(new java.io.InputStreamReader(process.getInputStream()))) {
                String line;
                while ((line = reader.readLine()) != null) output.append(line).append("\n");
            }
            int exitCode = process.waitFor();
            String out = output.toString().trim();
            return new ToolResult(exitCode == 0, out, exitCode == 0 ? null : "git exited with " + exitCode);
        } catch (Exception e) {
            return new ToolResult(false, "", e.getMessage());
        }
    }
}
