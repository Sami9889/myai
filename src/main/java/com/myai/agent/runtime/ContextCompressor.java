package com.myai.agent.runtime;

import java.util.List;
import java.util.Map;
import java.util.ArrayList;

public class ContextCompressor {
    private int maxTokens;

    public ContextCompressor(int maxTokens) {
        this.maxTokens = maxTokens;
    }

    public int estimate(String text) {
        return Math.max(1, text.getBytes(java.nio.charset.StandardCharsets.UTF_8).length / 4);
    }

    public List<Map<String, String>> compress(List<Map<String, String>> messages) {
        int total = 0;
        for (Map<String, String> m : messages) {
            total += estimate(m.getOrDefault("content", ""));
        }
        if (total <= maxTokens) return messages;
        List<Map<String, String>> kept = new ArrayList<>();
        total = 0;
        for (int i = messages.size() - 1; i >= 0; i--) {
            Map<String, String> message = messages.get(i);
            int cost = estimate(message.getOrDefault("content", ""));
            if (total + cost > maxTokens && !kept.isEmpty()) break;
            kept.add(message);
            total += cost;
        }
        List<Map<String, String>> result = new ArrayList<>(kept.size());
        for (int i = kept.size() - 1; i >= 0; i--) result.add(kept.get(i));
        return result;
    }
}
