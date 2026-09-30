package com.myai.agent.runtime;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.*;

public class TaskList {
    private Path path;
    private List<TaskItem> items;

    public record TaskItem(int id, String title, boolean done, String createdAt, String completedAt) {
    }

    public TaskList(String workspace) {
        this.path = Path.of(workspace).toAbsolutePath().normalize().resolve(".myai-tasks.json");
        this.items = new ArrayList<>();
        load();
    }

    private static String now() {
        return Instant.now().toString();
    }

    private void load() {
        if (!Files.exists(path)) return;
        try {
            String content = Files.readString(path);
            List<TaskItem> loaded = new ArrayList<>();
            int i = 0;
            while (i < content.length()) {
                int objStart = content.indexOf('{', i);
                if (objStart < 0) break;
                int objEnd = findMatchingBrace(content, objStart);
                String obj = content.substring(objStart, objEnd + 1);
                int id = Integer.parseInt(extractJsonField(obj, "id"));
                String title = extractJsonField(obj, "title");
                boolean done = Boolean.parseBoolean(extractJsonField(obj, "done"));
                String createdAt = extractJsonField(obj, "created_at");
                String completedAt = extractJsonField(obj, "completed_at");
                loaded.add(new TaskItem(id, title, done, createdAt, completedAt));
                i = objEnd + 1;
            }
            this.items = loaded;
        } catch (Exception e) {
            this.items = new ArrayList<>();
        }
    }

    private static int findMatchingBrace(String s, int start) {
        int depth = 0;
        for (int i = start; i < s.length(); i++) {
            if (s.charAt(i) == '{') depth++;
            else if (s.charAt(i) == '}') { depth--; if (depth == 0) return i; }
        }
        return s.length() - 1;
    }

    private static String extractJsonField(String obj, String field) {
        String pattern = "\"" + field + "\"";
        int idx = obj.indexOf(pattern);
        if (idx < 0) return "";
        int colon = obj.indexOf(':', idx + pattern.length());
        if (colon < 0) return "";
        int valStart = colon + 1;
        while (valStart < obj.length() && Character.isWhitespace(obj.charAt(valStart))) valStart++;
        if (valStart >= obj.length()) return "";
        if (obj.charAt(valStart) == '"') {
            int end = valStart + 1;
            while (end < obj.length()) {
                if (obj.charAt(end) == '"' && obj.charAt(end - 1) != '\\') break;
                end++;
            }
            return obj.substring(valStart + 1, end).replace("\\\"", "\"").replace("\\\\", "\\");
        } else {
            int end = valStart;
            while (end < obj.length() && !",}\n\r".contains(String.valueOf(obj.charAt(end)))) end++;
            return obj.substring(valStart, end).trim();
        }
    }

    private void save() {
        StringBuilder sb = new StringBuilder("[\n");
        for (int i = 0; i < items.size(); i++) {
            TaskItem item = items.get(i);
            sb.append("  {");
            sb.append("\"id\": ").append(item.id()).append(", ");
            sb.append("\"title\": \"").append(escapeJson(item.title())).append("\", ");
            sb.append("\"done\": ").append(item.done()).append(", ");
            sb.append("\"created_at\": \"").append(item.createdAt()).append("\", ");
            sb.append("\"completed_at\": \"").append(item.completedAt()).append("\"");
            sb.append("}");
            if (i < items.size() - 1) sb.append(",");
            sb.append("\n");
        }
        sb.append("]\n");
        try {
            Files.writeString(path, sb.toString());
        } catch (IOException e) {
            throw new RuntimeException("Failed to save tasks: " + e.getMessage(), e);
        }
    }

    private static String escapeJson(String s) {
        return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t");
    }

    public TaskItem add(String title) {
        int nextId = items.stream().mapToInt(TaskItem::id).max().orElse(0) + 1;
        TaskItem item = new TaskItem(nextId, title.strip(), false, now(), "");
        if (item.title().isEmpty()) throw new IllegalArgumentException("task title cannot be empty");
        items.add(item);
        save();
        return item;
    }

    public TaskItem complete(int taskId) {
        for (TaskItem item : items) {
            if (item.id() == taskId) {
                TaskItem updated = new TaskItem(item.id(), item.title(), true, item.createdAt(), now());
                int idx = items.indexOf(item);
                items.set(idx, updated);
                save();
                return updated;
            }
        }
        throw new IllegalArgumentException("task " + taskId + " was not found");
    }

    public int clearCompleted() {
        int before = items.size();
        items = new ArrayList<>(items.stream().filter(item -> !item.done()).toList());
        save();
        return before - items.size();
    }

    public String render() {
        if (items.isEmpty()) return "No tasks. Add one with: todo add \"task description\"";
        StringBuilder sb = new StringBuilder();
        for (TaskItem item : items) {
            sb.append("[").append(item.done() ? 'x' : ' ').append("] ").append(item.id()).append(": ").append(item.title()).append("\n");
        }
        return sb.toString().stripTrailing();
    }

    public static String toJsonValue(Object value) {
        if (value instanceof String s) return "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
        if (value instanceof Boolean b) return String.valueOf(b);
        if (value instanceof Number n) return String.valueOf(n);
        if (value instanceof Map<?, ?> map) {
            StringBuilder sb = new StringBuilder("{");
            int count = 0;
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                if (count++ > 0) sb.append(",");
                sb.append("\"").append(entry.getKey()).append("\":").append(toJsonValue(entry.getValue()));
            }
            return sb.append("}").toString();
        }
        if (value instanceof List<?> list) {
            StringBuilder sb = new StringBuilder("[");
            for (int i = 0; i < list.size(); i++) {
                if (i > 0) sb.append(",");
                sb.append(toJsonValue(list.get(i)));
            }
            return sb.append("]").toString();
        }
        return String.valueOf(value);
    }
}
