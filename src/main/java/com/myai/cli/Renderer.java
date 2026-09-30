package com.myai.cli;

import java.io.IOException;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class Renderer {
    public static final String RESET = "\033[0m";
    public static final String BOLD = "\033[1m";
    public static final String CYAN = "\033[36m";
    public static final String GREEN = "\033[32m";
    public static final String YELLOW = "\033[33m";
    public static final String RED = "\033[31m";
    public static final String DIM = "\033[2m";

    private boolean colour;

    public Renderer() {
        this(null);
    }

    public Renderer(Boolean colour) {
        this.colour = colour != null ? colour : System.getenv("NO_COLOR") == null;
    }

    public String paint(String text, String code) {
        return colour ? code + text + RESET : text;
    }

    public String dim(String text) { return paint(text, DIM); }
    public String bold(String text) { return paint(text, BOLD); }
    public String cyan(String text) { return paint(text, CYAN); }
    public String green(String text) { return paint(text, GREEN); }
    public String yellow(String text) { return paint(text, YELLOW); }
    public String red(String text) { return paint(text, RED); }

    private String safeText(String text) {
        if (text == null || text.isEmpty()) return text;
        return text.replaceAll("[^\\x00-\\x7F]", "");
    }

    public String panel(String title, String body, Integer width) {
        int w = width != null ? width : Math.min(96, Math.max(56, 78));
        int inner = Math.max(10, w - 4);
        List<String> lines = new ArrayList<>();
        for (String line : (safeText(body) != null ? safeText(body) : "").split("\n")) {
            if (line.isEmpty()) {
                lines.add("");
            } else {
                int start = 0;
                while (start < line.length()) {
                    int end = Math.min(start + inner, line.length());
                    lines.add(line.substring(start, end));
                    start = end;
                }
            }
        }
        StringBuilder sb = new StringBuilder();
        sb.append(paint("+" + "=".repeat(w - 2) + "+", CYAN)).append("\n");
        sb.append(paint("| " + title.substring(0, Math.min(inner, title.length())).formatted("%" + inner + "s") + " |", BOLD)).append("\n");
        for (String line : lines) {
            sb.append("| ").append(line.formatted("%" + inner + "s")).append(" |\n");
        }
        sb.append(paint("+" + "=".repeat(w - 2) + "+", CYAN));
        return sb.toString();
    }

    public String banner() {
        return paint("myai :: LOCAL CODING AGENT", BOLD + CYAN);
    }

    public String session(String workspace) {
        String timestamp = java.time.Instant.now().toString();
        return paint("workspace=" + workspace + " | mode=offline | started=" + timestamp, DIM);
    }

    public String activity(String phase, String detail) {
        String timestamp = java.time.Instant.now().toString().substring(11, 19);
        String label = "[" + timestamp + "] " + phase.toUpperCase();
        return paint(label.formatted("%-20s", 20), YELLOW) + " " + detail;
    }

    public String footer() {
        return paint("-".repeat(60), DIM);
    }

    public String prompt() {
        return paint("you> ", BOLD + CYAN);
    }

    public String user(String text) { return panel(paint(" user ", CYAN), text); }
    public String agent(String text) { return panel(paint(" agent ", GREEN), text); }
    public String error(String text) { return panel(paint(" error ", RED), text); }
}
