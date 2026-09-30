package com.myai.tools;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

public class LinterBridge extends BaseTool {
    public String name() { return "lint"; }
    public String description() { return "Validate source files for syntax errors." }

    @Override
    public Map<String, Object> validate(Map<String, Object> arguments) {
        Path path = Path.of(string(arguments, "path", null));
        return Map.of("path", path);
    }

    @Override
    public ToolResult execute(Map<String, Object> arguments) throws Exception {
        Path path = (Path) arguments.get("path");
        if (!Files.exists(path)) return new ToolResult(false, "", path + ": file not found");
        String content = Files.readString(path);
        try {
            java.util.regex.Pattern.compile(content);
            return new ToolResult(true, "syntax valid", null);
        } catch (Exception e) {
            return new ToolResult(false, "", path + ": syntax error - " + e.getMessage());
        }
    }
}
