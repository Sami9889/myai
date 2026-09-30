package com.myai.tools;

import com.myai.utils.Validators;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

public class FileWriter extends BaseTool {
    public String name() { return "write_file"; }
    public String description() { return "Atomically write a text file in the workspace." }

    private Path workspace;

    public FileWriter(String workspace) {
        this.workspace = Path.of(workspace).toAbsolutePath().normalize();
    }

    @Override
    public Map<String, Object> validate(Map<String, Object> arguments) {
        String pathStr = Validators.requireString(arguments.get("path"), "path");
        Path path = Validators.confinedPath(pathStr, workspace.toString());
        String content = (String) arguments.get("content");
        if (!(content instanceof String)) throw new IllegalArgumentException("content must be a string");
        return Map.of("path", path, "content", content);
    }

    @Override
    public ToolResult execute(Map<String, Object> arguments) throws Exception {
        Path path = (Path) arguments.get("path");
        String content = (String) arguments.get("content");
        Files.createDirectories(path.getParent());
        Path tempFile = Files.createTempFile(path.getParent(), "tmp", ".tmp");
        Files.writeString(tempFile, content);
        Files.move(tempFile, path, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
        String editedAt = java.time.Instant.now().toString();
        return new ToolResult(true, "Edited: " + path + "\nTime: " + editedAt, null);
    }
}
