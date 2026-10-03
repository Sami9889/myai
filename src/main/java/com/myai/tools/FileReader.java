package com.myai.tools;

import com.myai.utils.Validators;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

public class FileReader extends BaseTool {
    public String name() { return "read_file"; }
    public String description() { return "Read a bounded text file from the workspace."; }

    private Path workspace;

    public FileReader(String workspace) {
        this.workspace = Path.of(workspace).toAbsolutePath().normalize();
    }

    @Override
    public Map<String, Object> validate(Map<String, Object> arguments) {
        String pathStr = Validators.requireString(arguments.get("path"), "path");
        Path path = Validators.confinedPath(pathStr, workspace.toString());
        int start = Validators.requireInt(arguments.getOrDefault("start", 0), "start", 0);
        int end = arguments.containsKey("end") ? Validators.requireInt(arguments.get("end"), "end", start) : -1;
        return Map.of("path", path, "start", start, "end", end);
    }

    @Override
    public ToolResult execute(Map<String, Object> arguments) throws Exception {
        Path path = (Path) arguments.get("path");
        int start = (Integer) arguments.get("start");
        int end = (Integer) arguments.get("end");
        String content = Files.readString(path);
        String[] lines = content.split("\n", -1);
        StringBuilder sb = new StringBuilder();
        int endIdx = end >= 0 ? Math.min(end, lines.length) : lines.length;
        for (int i = start; i < endIdx; i++) {
            sb.append(lines[i]);
            if (i < endIdx - 1) sb.append("\n");
        }
        return new ToolResult(true, sb.toString(), null);
    }
}
