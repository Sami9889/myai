package com.myai.tools;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.*;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class WebSearch extends BaseTool {
    public String name() { return "web_search"; }
    public String description() { return "Search the web for up-to-date information using Bing."; }

    private boolean allowNetwork;
    private int timeout;

    public WebSearch(boolean allowNetwork, int timeout) {
        this.allowNetwork = allowNetwork;
        this.timeout = timeout;
    }

    @Override
    public Map<String, Object> validate(Map<String, Object> arguments) {
        if (!allowNetwork) throw new IllegalArgumentException("network access is disabled");
        String query = string(arguments, "query", null);
        int numResults = arguments.containsKey("num_results") ? ((Number) arguments.get("num_results")).intValue() : 5;
        if (numResults < 1 || numResults > 10) throw new IllegalArgumentException("num_results must be between 1 and 10");
        return Map.of("query", query, "num_results", numResults);
    }

    @Override
    public ToolResult execute(Map<String, Object> arguments) throws Exception {
        String query = (String) arguments.get("query");
        int numResults = (Integer) arguments.get("num_results");
        try {
            String urlStr = "https://www.bing.com/search?q=" + java.net.URLEncoder.encode(query, "UTF-8") + "&count=" + numResults;
            HttpURLConnection conn = (HttpURLConnection) new URL(urlStr).openConnection();
            conn.setRequestProperty("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36");
            conn.setConnectTimeout(timeout * 1000);
            conn.setReadTimeout(timeout * 1000);
            try (var in = new java.io.InputStreamReader(conn.getInputStream())) {
                StringBuilder sb = new StringBuilder();
                char[] buf = new char[4096];
                int len;
                while ((len = in.read(buf)) >= 0) sb.append(buf, 0, len);
                String html = sb.toString();
                List<Map<String, String>> results = new ArrayList<>();
                Matcher m = Pattern.compile("<li class=\"b_algo\"[^>]*>(.*?)</li>", Pattern.DOTALL).matcher(html);
                while (m.find()) {
                    String snippet = m.group(1);
                    String title = extractTag(snippet, "div class=\"tptt\"");
                    String url = extractTag(snippet, "cite");
                    if (!title.isEmpty() && !url.isEmpty()) {
                        results.add(Map.of("title", title, "url", url, "snippet", snippet.replaceAll("<.*?>", "").replaceAll("\\s+", " ").strip()));
                    }
                    if (results.size() >= numResults) break;
                }
                if (results.isEmpty()) return new ToolResult(true, "No web results for: " + query, null);
                StringBuilder out = new StringBuilder();
                for (int i = 0; i < results.size(); i++) {
                    Map<String, String> r = results.get(i);
                    out.append(i + 1).append(". ").append(r.get("title")).append("\n   ").append(r.get("url")).append("\n   ").append(r.get("snippet").substring(0, Math.min(300, r.get("snippet").length()))).append("\n\n");
                }
                return new ToolResult(true, out.toString().trim(), null);
            }
        } catch (Exception e) {
            return new ToolResult(false, "", "web search failed: " + e.getClass().getSimpleName() + ": " + e.getMessage());
        }
    }

    private static String extractTag(String html, String tag) {
        Pattern p = Pattern.compile("<" + tag + "[^>]*>(.*?)</" + tag.split(" ")[0] + ">", Pattern.DOTALL);
        Matcher m = p.matcher(html);
        if (m.find()) {
            return m.group(1).replaceAll("<.*?>", "").trim();
        }
        return "";
    }
}
