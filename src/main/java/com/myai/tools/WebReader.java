package com.myai.tools;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.*;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class WebReader extends BaseTool {
    public String name() { return "web_read"; }
    public String description() { return "Fetch a webpage and return its readable text content." }

    private boolean allowNetwork;
    private int timeout;

    public WebReader(boolean allowNetwork, int timeout) {
        this.allowNetwork = allowNetwork;
        this.timeout = timeout;
    }

    @Override
    public Map<String, Object> validate(Map<String, Object> arguments) {
        if (!allowNetwork) throw new IllegalArgumentException("network access is disabled");
        String url = string(arguments, "url", null);
        if (!url.startsWith("http://") && !url.startsWith("https://")) throw new IllegalArgumentException("url must start with http:// or https://");
        int maxChars = arguments.containsKey("max_chars") ? ((Number) arguments.get("max_chars")).intValue() : 4000;
        if (maxChars < 100 || maxChars > 20000) throw new IllegalArgumentException("max_chars must be between 100 and 20000");
        return Map.of("url", url, "max_chars", maxChars);
    }

    @Override
    public ToolResult execute(Map<String, Object> arguments) throws Exception {
        String url = (String) arguments.get("url");
        int maxChars = (Integer) arguments.get("max_chars");
        try {
            HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
            conn.setRequestProperty("User-Agent", "myai/0.1 (local agent)");
            conn.setConnectTimeout(timeout * 1000);
            conn.setReadTimeout(timeout * 1000);
            try (var in = new java.io.InputStreamReader(conn.getInputStream())) {
                StringBuilder sb = new StringBuilder();
                char[] buf = new char[4096];
                int len;
                while ((len = in.read(buf)) >= 0) sb.append(buf, 0, len);
                String html = sb.toString();
                StringBuilder text = new StringBuilder();
                Pattern tagPattern = Pattern.compile("<(script|style|nav|header|footer|aside)[^>]*>.*?</(script|style|nav|header|footer|aside)>", Pattern.DOTALL | Pattern.CASE_INSENSITIVE);
                html = tagPattern.matcher(html).replaceAll("");
                Matcher m = Pattern.compile(">([^<]+)<").matcher(html);
                while (m.find()) {
                    String content = m.group(1).trim();
                    if (!content.isEmpty()) text.append(content).append("\n");
                }
                String result = text.toString().replaceAll("\\n{3,}", "\n\n").trim();
                if (result.length() > maxChars) result = result.substring(0, maxChars) + "\n...[truncated]";
                return new ToolResult(true, result, null);
            }
        } catch (Exception e) {
            return new ToolResult(false, "", "failed to fetch " + url + ": " + e.getClass().getSimpleName() + ": " + e.getMessage());
        }
    }
}
