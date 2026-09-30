package com.myai.agent.runtime;

import com.myai.core.engine.TensorOps;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

public class MemoryStore {
    public record Memory(String text, List<Double> vector, Map<String, String> metadata) {
    }

    private Path path;
    private List<Memory> items;

    public MemoryStore(String path) {
        this.path = path != null ? Path.of(path) : null;
        this.items = new ArrayList<>();
        load();
    }

    private void load() {
        if (path == null || !Files.exists(path)) return;
        try {
            String content = Files.readString(path);
            int i = 0;
            while (i < content.length()) {
                int objStart = content.indexOf('{', i);
                if (objStart < 0) break;
                int objEnd = findMatchingBrace(content, objStart);
                String obj = content.substring(objStart, objEnd + 1);
                String text = extractJsonField(obj, "text");
                List<Double> vector = new ArrayList<>();
                String vectorStr = extractJsonField(obj, "vector");
                if (!vectorStr.isEmpty()) {
                    vectorStr = vectorStr.replace("[", "").replace("]", "").trim();
                    if (!vectorStr.isEmpty()) {
                        for (String part : vectorStr.split(",")) {
                            vector.add(Double.parseDouble(part.trim()));
                        }
                    }
                }
                Map<String, String> metadata = new LinkedHashMap<>();
                String metaStr = extractJsonField(obj, "metadata");
                if (!metaStr.isEmpty()) {
                    metaStr = metaStr.replace("{", "").replace("}", "").trim();
                    for (String entry : metaStr.split(",")) {
                        String[] kv = entry.split(":", 2);
                        if (kv.length == 2) {
                            metadata.put(kv[0].trim().replace("\"", ""), kv[1].trim().replace("\"", ""));
                        }
                    }
                }
                items.add(new Memory(text, vector, metadata));
                i = objEnd + 1;
            }
        } catch (Exception e) {
            items = new ArrayList<>();
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

    public void save() {
        if (path == null) return;
        StringBuilder sb = new StringBuilder("[\n");
        for (int i = 0; i < items.size(); i++) {
            Memory m = items.get(i);
            sb.append("  {");
            sb.append("\"text\": \"").append(escapeJson(m.text())).append("\", ");
            sb.append("\"vector\": [");
            for (int j = 0; j < m.vector().size(); j++) {
                if (j > 0) sb.append(",");
                sb.append(m.vector().get(j));
            }
            sb.append("], ");
            sb.append("\"metadata\": {");
            int mc = 0;
            for (Map.Entry<String, String> e : m.metadata().entrySet()) {
                if (mc++ > 0) sb.append(",");
                sb.append("\"").append(e.getKey()).append("\": \"").append(e.getValue()).append("\"");
            }
            sb.append("}");
            sb.append("}");
            if (i < items.size() - 1) sb.append(",");
            sb.append("\n");
        }
        sb.append("]\n");
        try {
            Files.writeString(path, sb.toString());
        } catch (IOException e) {
            throw new RuntimeException("Failed to save memory: " + e.getMessage(), e);
        }
    }

    private static String escapeJson(String s) {
        return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t");
    }

    public void add(String text, List<Double> vector, Map<String, String> metadata) {
        items.add(new Memory(text, vector, metadata != null ? metadata : new LinkedHashMap<>()));
        save();
    }

    public List<Map.Entry<Double, Memory>> search(List<Double> vector, int limit) {
        List<Map.Entry<Double, Memory>> results = new ArrayList<>();
        for (Memory m : items) {
            double sim = TensorOps.cosineSimilarity(vector, m.vector());
            results.add(Map.entry(sim, m));
        }
        results.sort((a, b) -> Double.compare(b.getKey(), a.getKey()));
        return results.subList(0, Math.min(limit, results.size()));
    }
}
