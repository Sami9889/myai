package com.myai.tools;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class HelpSearch extends BaseTool {
    public String name() { return "search"; }
    public String description() { return "Search local project documentation and source without network access." }

    private Set<String> extensions = Set.of(".md", ".txt", ".py", ".toml", ".json", ".sh", ".java");
    private Path workspace;

    public HelpSearch(String workspace) {
        this.workspace = Path.of(workspace).toAbsolutePath().normalize();
    }

    @Override
    public Map<String, Object> validate(Map<String, Object> arguments) {
        String query = string(arguments, "query", null);
        int limit = arguments.containsKey("limit") ? ((Number) arguments.get("limit")).intValue() : 8;
        if (limit < 1 || limit > 50) throw new IllegalArgumentException("limit must be between 1 and 50");
        return Map.of("query", query.toLowerCase(), "limit", limit);
    }

    @Override
    public ToolResult execute(Map<String, Object> arguments) throws Exception {
        String query = (String) arguments.get("query");
        int limit = (Integer) arguments.get("limit");
        List<String> terms = new ArrayList<>();
        Matcher m = Pattern.compile("[a-z0-9_]+").matcher(query);
        while (m.find()) {
            String term = m.group();
            if (term.length() > 1) terms.add(term);
        }
        if (terms.isEmpty()) return new ToolResult(false, "", "search query must contain letters or numbers");

        Set<String> ignored = Set.of(".git", ".venv", "__pycache__", "build", "dist");
        List<int[]> results = new ArrayList<>();
        try (var stream = Files.walk(workspace)) {
            List<Path> paths = new ArrayList<>();
            stream.forEach(p -> paths.add(p));
            for (Path path : paths) {
                if (!Files.isRegularFile(path)) continue;
                String fileName = path.getFileName().toString();
                if (fileName.equals(".myai-tasks.json")) continue;
                String ext = getExtension(fileName);
                if (!extensions.contains(ext)) continue;
                Path relative = workspace.relativize(path);
                if (ignored.contains(relative.getName(0).toString())) continue;
                try {
                    List<String> lines = Files.readAllLines(path);
                    for (int i = 0; i < lines.size(); i++) {
                        String line = lines.get(i);
                        String lower = line.toLowerCase();
                        int score = 0;
                        for (String term : terms) score += countOccurrences(lower, term);
                        if (score > 0) {
                            results.add(new int[]{score, relative.toString().hashCode(), i});
                        }
                    }
                } catch (Exception e) {
                    // skip unreadable files
                }
            }
        }
        results.sort((a, b) -> {
            if (b[0] != a[0]) return b[0] - a[0];
            return Integer.compare(a[1], b[1]);
        });
        if (results.isEmpty()) return new ToolResult(true, "No local results for: " + query, null);
        StringBuilder sb = new StringBuilder();
        int count = 0;
        try (var stream = Files.walk(workspace)) {
            List<Path> paths = new ArrayList<>();
            stream.forEach(p -> paths.add(p));
            for (int[] r : results) {
                if (count >= limit) break;
                for (Path path : paths) {
                    if (!Files.isRegularFile(path)) continue;
                    Path relative = workspace.relativize(path);
                    if (relative.toString().hashCode() != r[1]) continue;
                    try {
                        List<String> lines = Files.readAllLines(path);
                        sb.append(relative).append(": ").append(lines.get(r[2])).append("\n");
                        count++;
                        break;
                    } catch (Exception e) {}
                }
            }
        }
        return new ToolResult(true, sb.toString().trim(), null);
    }

    private static String getExtension(String fileName) {
        int idx = fileName.lastIndexOf('.');
        return idx >= 0 ? fileName.substring(idx).toLowerCase() : "";
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
