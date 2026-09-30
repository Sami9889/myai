package com.myai.agent.runtime;

import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;

public class Conversation {
    public static String localReply(String text) {
        String normalized = text.toLowerCase().strip();
        if (normalized.isEmpty()) {
            return "I am here. Tell me what you want to inspect, change, search, or run.";
        }
        switch (normalized) {
            case "hi", "hello", "hey", "yo", "good morning", "good afternoon", "good evening" ->
                return "Hello. I am here and ready to work in this repository. You can ask me naturally, such as \"show me the Python files\" or \"read the README\".";
            case "are you there", "are you here", "you there", "can you hear me" ->
                return "Yes, I am here. I can read, write, edit, search, lint, manage TODOs, inspect Git, and install this repository within the workspace.";
            case "what are you", "who are you", "what is this" ->
                return "I am myai, a local-only repository assistant. I use the tools in this checkout and do not use cloud inference or external AI backends.";
            case "what can you do", "how can you help", "what do you do" ->
                return "I can inspect the repository, read and edit files, search local source and docs, create TODOs, lint Python, run diagnostics, inspect Git, and install the current checkout. Ask in ordinary language.";
            case "thanks", "thank you", "thx" ->
                return "You are welcome. I am ready for the next task.";
            case "stop", "cancel", "never mind", "nevermind" ->
                return "Okay. I will not change anything.";
            default -> {
                if (normalized.contains("what time") || normalized.contains("current time") || normalized.contains("time is it")) {
                    return Instant.now().atZone(ZoneId.systemDefault()).format(DateTimeFormatter.ofPattern("It is yyyy-MM-dd HH:mm:ss z."));
                }
                return null;
            }
        }
    }
}
