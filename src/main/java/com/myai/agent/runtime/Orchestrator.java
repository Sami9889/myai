package com.myai.agent.runtime;

import com.myai.tools.BaseTool;
import com.myai.tools.ToolResult;

import java.util.*;
import java.util.function.Function;
import java.util.regex.Pattern;

public class Orchestrator {
    public static final Pattern TOOL_PATTERN = Pattern.compile("<tool\\s+name=[\"'](?P<name>[\\w.-]+)[\"']\\s*>(?P<body>.*?)</tool>", Pattern.DOTALL | Pattern.CASE_INSENSITIVE);
    public static final Pattern JSON_PATTERN = Pattern.compile("```tool\\s*(?P<body>\\{.*?\\})\\s*```", Pattern.DOTALL | Pattern.CASE_INSENSITIVE);

    private final Function<List<Map<String, String>>, String> model;
    private final Map<String, BaseTool> tools;
    private final ContextCompressor compressor;
    private final List<Map<String, String>> messages;
    private final AgentConfig config;
    private SessionState state;

    public Orchestrator(Function<List<Map<String, String>>, String> model, Map<String, BaseTool> tools, AgentConfig config) {
        this.model = model;
        this.tools = tools != null ? tools : new LinkedHashMap<>();
        this.config = config != null ? config : new AgentConfig();
        this.compressor = new ContextCompressor(this.config.maxContextTokens());
        this.messages = new ArrayList<>();
        this.state = new SessionState();
    }

    public void register(BaseTool tool) {
        this.tools.put(tool.name(), tool);
    }

    public Map<String, BaseTool> tools() {
        return this.tools;
    }

    public AgentResponse run(String task) {
        this.state = new SessionState(task);
        this.messages.clear();
        this.messages.add(Map.of("role", "system", "content", "You are a local-only agent. Use <tool name=\"name\">{json}</tool> for tools."));
        this.messages.add(Map.of("role", "user", "content", task));
        List<ToolResult> results = new ArrayList<>();
        Map<String, Integer> seen = new LinkedHashMap<>();
        String answer = "";
        boolean modelConfigured = this.model != null;
        int maxSteps = Math.max(1, config != null ? config.maxSteps() : 32);

        for (int step = 0; step < maxSteps; step++) {
            this.state.transition(SessionStatus.THINKING);
            List<Map<String, String>> context = this.compressor.compress(this.messages);
            String generated = this.model != null ? this.model.apply(context) : null;
            if (generated == null) {
                generated = fallback(task, modelConfigured);
                this.messages.add(Map.of("role", "assistant", "content", generated));
                this.state.transition(SessionStatus.COMPLETE);
                return new AgentResponse(reflect(task, generated, results), this.state, results);
            }
            List<Map.Entry<String, Map<String, Object>>> calls = parseCalls(generated);
            if (calls.isEmpty()) {
                answer = generated;
                this.messages.add(Map.of("role", "assistant", "content", generated));
                this.state.transition(SessionStatus.COMPLETE);
                return new AgentResponse(reflect(task, answer, results), this.state, results);
            }
            String actionKey = serializeCalls(calls);
            seen.put(actionKey, seen.getOrDefault(actionKey, 0) + 1);
            if (seen.get(actionKey) > (config != null ? config.maxRepeatedActions() : 3)) {
                answer = "The same tool request repeated too many times; execution stopped for safety.";
                this.state.fail(answer);
                return new AgentResponse(answer, this.state, results);
            }
            this.messages.add(Map.of("role", "assistant", "content", generated));
            for (Map.Entry<String, Map<String, Object>> entry : calls) {
                results.add(invoke(entry.getKey(), entry.getValue()));
            }
        }
        answer = "Maximum agent steps reached without a final response.";
        this.state.fail(answer);
        return new AgentResponse(answer, this.state, results);
    }

    private List<Map.Entry<String, Map<String, Object>>> parseCalls(String text) {
        List<Map.Entry<String, Map<String, Object>>> calls = new ArrayList<>();
        var toolMatcher = Orchestrator.TOOL_PATTERN.matcher(text);
        while (toolMatcher.find()) {
            String body = toolMatcher.group("body").trim();
            Map<String, Object> arguments;
            try {
                arguments = parseJsonObject(body);
            } catch (Exception e) {
                arguments = new LinkedHashMap<>();
                arguments.put("input", body);
            }
            calls.add(Map.entry(toolMatcher.group("name"), arguments));
        }
        var jsonMatcher = Orchestrator.JSON_PATTERN.matcher(text);
        while (jsonMatcher.find()) {
            try {
                Map<String, Object> payload = parseJsonObject(jsonMatcher.group("body"));
                String name = (String) payload.remove("name");
                calls.add(Map.entry(name, payload));
            } catch (Exception e) {
                continue;
            }
        }
        return calls;
    }

    private ToolResult invoke(String name, Map<String, Object> arguments) {
        BaseTool tool = this.tools.get(name);
        if (tool == null) return new ToolResult(false, "", "unknown tool: " + name);
        this.state.transition(SessionStatus.TOOL, "tool:" + name);
        ToolResult result = tool.run(arguments);
        String content = "{\"name\":\"" + escapeJson(name) + "\",\"ok\":" + result.ok() + ",\"output\":\"" + escapeJson(result.output()) + "\",\"error\":" + (result.error() == null ? "null" : "\"" + escapeJson(result.error()) + "\"") + "}";
        this.messages.add(Map.of("role", "tool", "content", content));
        return result;
    }

    private static String escapeJson(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t");
    }

    private String fallback(String task, boolean modelConfigured) {
        String conversational = Conversation.localReply(task);
        if (conversational != null) return conversational;
        if (modelConfigured) {
            return "Task received: " + task + "\n\nThe local model is configured but produced unreadable output. The CLI remains useful for deterministic workspace tools. Try `diagnostics`, `walk *.py`, `read README.md`, or `lint PATH`.";
        }
        return "Task received: " + task + "\n\nNeural generation is unavailable because config.json has no local model path configured. The CLI is online and its deterministic workspace tools are ready. Try `diagnostics`, `walk *.py`, `read README.md`, or `lint PATH`.";
    }

    private String reflect(String task, String answer, List<ToolResult> results) {
        long failures = results.stream().filter(r -> !r.ok()).count();
        if (failures > 0) return answer + "\n\nRecovery: " + failures + " tool operation(s) failed; inspect the reported errors before retrying.";
        return answer;
    }

    private String serializeCalls(List<Map.Entry<String, Map<String, Object>>> calls) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < calls.size(); i++) {
            if (i > 0) sb.append(",");
            Map.Entry<String, Map<String, Object>> entry = calls.get(i);
            sb.append("{\"name\":\"").append(escapeJson(entry.getKey())).append("\",\"args\":").append(TaskList.toJsonValue(entry.getValue())).append("}");
        }
        sb.append("]");
        return sb.toString();
    }

    public void reset() {
        this.messages.clear();
        this.state = new SessionState();
    }

    public Map<String, Object> snapshot() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("state", this.state.snapshot());
        m.put("messages", this.messages.size());
        m.put("tools", new ArrayList<>(this.tools.keySet()).stream().sorted().toList());
        return m;
    }

    private static Map<String, Object> parseJsonObject(String s) {
        Map<String, Object> result = new LinkedHashMap<>();
        s = s.trim();
        if (!s.startsWith("{") || !s.endsWith("}")) throw new IllegalArgumentException("Not a JSON object");
        s = s.substring(1, s.length() - 1).trim();
        if (s.isEmpty()) return result;
        int i = 0;
        while (i < s.length()) {
            while (i < s.length() && Character.isWhitespace(s.charAt(i))) i++;
            if (i >= s.length()) break;
            int colon = s.indexOf(':', i);
            if (colon < 0) break;
            String key = s.substring(i, colon).trim().replaceAll("^\"|\"$", "");
            i = colon + 1;
            while (i < s.length() && Character.isWhitespace(s.charAt(i))) i++;
            Object value;
            if (s.charAt(i) == '{') {
                int depth = 0;
                int j = i;
                while (j < s.length()) {
                    if (s.charAt(j) == '{') depth++;
                    if (s.charAt(j) == '}') depth--;
                    j++;
                    if (depth == 0) break;
                }
                value = parseJsonObject(s.substring(i, j));
                i = j;
            } else if (s.charAt(i) == '[') {
                int depth = 0;
                int j = i;
                while (j < s.length()) {
                    if (s.charAt(j) == '[') depth++;
                    if (s.charAt(j) == ']') depth--;
                    j++;
                    if (depth == 0) break;
                }
                value = parseJsonArray(s.substring(i, j));
                i = j;
            } else if (s.charAt(i) == '"') {
                int j = s.indexOf('"', i + 1);
                while (j >= 0 && s.charAt(j - 1) == '\\') j = s.indexOf('"', j + 1);
                if (j < 0) j = s.length();
                value = s.substring(i + 1, j).replace("\\\"", "\"").replace("\\\\", "\\");
                i = j + 1;
            } else {
                int j = i;
                while (j < s.length() && !",}".contains(String.valueOf(s.charAt(j)))) j++;
                String token = s.substring(i, j).trim();
                if (token.equals("true")) value = Boolean.TRUE;
                else if (token.equals("false")) value = Boolean.FALSE;
                else if (token.equals("null")) value = null;
                else {
                    try { value = Integer.parseInt(token); }
                    catch (Exception e) {
                        try { value = Double.parseDouble(token); }
                        catch (Exception e2) { value = token; }
                    }
                }
                i = j;
            }
            result.put(key, value);
            while (i < s.length() && (Character.isWhitespace(s.charAt(i)) || s.charAt(i) == ',')) i++;
        }
        return result;
    }

    @SuppressWarnings("unchecked")
    private static List<Object> parseJsonArray(String s) {
        List<Object> list = new ArrayList<>();
        s = s.trim();
        if (!s.startsWith("[") || !s.endsWith("]")) throw new IllegalArgumentException("Not a JSON array");
        s = s.substring(1, s.length() - 1).trim();
        if (s.isEmpty()) return list;
        int i = 0;
        while (i < s.length()) {
            while (i < s.length() && Character.isWhitespace(s.charAt(i))) i++;
            if (i >= s.length()) break;
            Object value;
            if (s.charAt(i) == '{') {
                int depth = 0;
                int j = i;
                while (j < s.length()) {
                    if (s.charAt(j) == '{') depth++;
                    if (s.charAt(j) == '}') depth--;
                    j++;
                    if (depth == 0) break;
                }
                value = parseJsonObject(s.substring(i, j));
                i = j;
            } else if (s.charAt(i) == '[') {
                int depth = 0;
                int j = i;
                while (j < s.length()) {
                    if (s.charAt(j) == '[') depth++;
                    if (s.charAt(j) == ']') depth--;
                    j++;
                    if (depth == 0) break;
                }
                value = parseJsonArray(s.substring(i, j));
                i = j;
            } else if (s.charAt(i) == '"') {
                int j = s.indexOf('"', i + 1);
                while (j >= 0 && s.charAt(j - 1) == '\\') j = s.indexOf('"', j + 1);
                if (j < 0) j = s.length();
                value = s.substring(i + 1, j).replace("\\\"", "\"").replace("\\\\", "\\");
                i = j + 1;
            } else {
                int j = i;
                while (j < s.length() && !",]".contains(String.valueOf(s.charAt(j)))) j++;
                String token = s.substring(i, j).trim();
                if (token.equals("true")) value = Boolean.TRUE;
                else if (token.equals("false")) value = Boolean.FALSE;
                else if (token.equals("null")) value = null;
                else {
                    try { value = Integer.parseInt(token); }
                    catch (Exception e) {
                        try { value = Double.parseDouble(token); }
                        catch (Exception e2) { value = token; }
                    }
                }
                i = j;
            }
            list.add(value);
            while (i < s.length() && (Character.isWhitespace(s.charAt(i)) || s.charAt(i) == ',')) i++;
        }
        return list;
    }
}
