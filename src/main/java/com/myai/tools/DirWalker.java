package com.myai.tools;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.Map;
import java.util.regex.Pattern;

public class DirWalker extends BaseTool {
    public String name() { return "walk"; }
    public String description() { return "Index files while respecting common ignore directories." }

    private Path workspace;

    public DirWalker(String workspace) {
        this.workspace = Path.of(workspace).toAbsolutePath().normalize();
    }

    @Override
    public Map<String, Object> validate(Map<String, Object> arguments) {
        return Map.of("pattern", arguments.getOrDefault("pattern", "*"));
    }

    @Override
    public ToolResult execute(Map<String, Object> arguments) throws Exception {
        String pattern = (String) arguments.get("pattern");
        Set<String> ignored = Set.of(".git", ".venv", "__pycache__", "node_modules");
        List<String> rows = new ArrayList<>();
        try (var stream = Files.walk(workspace)) {
            stream.forEach(path -> {
                if (path.toFile().isFile() && !ignored.contains(path.getFileName().toString())) {
                    Path relative = workspace.relativize(path);
                    if (matchesPattern(relative.toString(), pattern) || matchesPattern(path.getFileName().toString(), pattern)) {
                        rows.add(relative.toString().replace('\\', '/'));
                    }
                }
            });
        }
        Collections.sort(rows);
        return new ToolResult(true, String.join("\n", rows), null);
    }

    private static boolean matchesPattern(String str, String pattern) {
        StringBuilder regex = new StringBuilder();
        for (char c : pattern.toCharArray()) {
            switch (c) {
                case '*' -> regex.append(".*");
                case '?' -> regex.append(".");
                default -> regex.append(Pattern.quote(String.valueOf(c)));
            }
        }
        return Pattern.matches(regex.toString(), str);
    }
}
