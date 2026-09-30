package com.myai.tools;

import com.myai.utils.Validators;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

public class FilePatcher extends BaseTool {
    public String name() { return "patch_file"; }
    public String description() { return "Replace one exact block in a workspace file." }

    private final FileReader reader;
    private final FileWriter writer;

    public FilePatcher(String workspace) {
        this.reader = new FileReader(workspace);
        this.writer = new FileWriter(workspace);
    }

    @Override
    public Map<String, Object> validate(Map<String, Object> arguments) {
        String path = string(arguments, "path", null);
        String old = string(arguments, "old", null);
        String n = (String) arguments.get("new");
        if (!(n instanceof String)) throw new IllegalArgumentException("new must be a string");
        return Map.of("path", path, "old", old, "new", n);
    }

    @Override
    public ToolResult execute(Map<String, Object> arguments) throws Exception {
        Map<String, Object> validated = validate(arguments);
        ToolResult result = reader.run(validated);
        if (!result.ok()) return result;
        String output = result.output();
        String old = (String) validated.get("old");
        String n = (String) validated.get("new");
        if (countOccurrences(output, old) != 1) return new ToolResult(false, "", "old block must occur exactly once");
        String newContent = output.replace(old, n, 1);
        Map<String, Object> writeArgs = Map.of("path", validated.get("path"), "content", newContent);
        return writer.run(writeArgs);
    }

    private static int countOccurrences(String str, String sub) {
        int count = 0;
        int idx = 0;
        while ((idx = str.indexOf(sub, idx)) >= 0) {
            count++;
            idx += sub.length();
        }
        return count;
    }
}
