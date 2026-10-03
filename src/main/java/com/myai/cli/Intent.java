package com.myai.cli;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public record Intent(String command, List<String> arguments, String explanation) {
    private static final Pattern ADD_TASK = Pattern.compile("(?:add|create)\\s+(?:a\\s+)?(?:todo|task)\\s*(?:for|:)?\\s*(.+)", Pattern.CASE_INSENSITIVE);
    private static final Pattern COMPLETE_TASK = Pattern.compile("(?:complete|finish|mark)\\s+(?:task|todo)\\s+#?(\\d+)", Pattern.CASE_INSENSITIVE);
    private static final Pattern READ_FILE = Pattern.compile("(?:read|open|show|display)\\s+(?:the\\s+)?(?:file\\s+)?(.+)", Pattern.CASE_INSENSITIVE);
    private static final Pattern WRITE_FILE = Pattern.compile("(?:write|edit|create|add)\\s+(?:to\\s+)?(?:the\\s+)?file\\s+([^\\s]+)\\s+(?:with\\s+)?(.+)", Pattern.CASE_INSENSITIVE);
    private static final Pattern SEARCH = Pattern.compile("(?:find|search|look\\s+for)\\s+(?:help\\s+)?(?:about|for)?\\s*(.+)", Pattern.CASE_INSENSITIVE);
    private static final Pattern WALK = Pattern.compile("(?:list|show|find)\\s+(?:all\\s+)?(?:the\\s+)?(.+?)\\s+files?$", Pattern.CASE_INSENSITIVE);
    private static final Pattern LINT = Pattern.compile("(?:lint|check|validate)\\s+(?:the\\s+)?(?:file\\s+)?(.+)", Pattern.CASE_INSENSITIVE);
    private static final Pattern HOW_TO = Pattern.compile("(?:(?:how\\s+(?:do\\s+i|to)|explain)\\s+(.+)|what\\s+(?:is|are)\\s+(?:the\\s+)?(?:syntax|command|commands|usage)\\s+(?:for|of)\\s+(.+)|what\\s+(?:is|are)\\s+(.+?)\\s+(?:syntax|commands?))", Pattern.CASE_INSENSITIVE);
    private static final Pattern GIT_READ = Pattern.compile("(?:show\\s+|check\\s+)?git\\s+(status|diff|log|branch)\\b", Pattern.CASE_INSENSITIVE);
    private static final Pattern LEARN = Pattern.compile("(?:learn|study)\\s+(?:from\\s+)?(?:this\\s+)?(?:workspace|repository|repo|project|codebase|code)", Pattern.CASE_INSENSITIVE);

    public Intent {
        arguments = List.copyOf(arguments);
    }

    public static Intent parseIntent(String text) {
        String original = text.strip();
        if (original.isEmpty()) return null;
        String lowered = original.toLowerCase();
        if ("help".equals(lowered)) return new Intent("help", List.of(), "show available capabilities");
        if (LEARN.matcher(original).find()) return new Intent("learn", List.of(), "learning from local workspace files");
        if (lowered.contains("what time") || lowered.contains("current time") || lowered.contains("time is it"))
            return new Intent("time", List.of(), "show the local time");
        if (lowered.contains("repo status") || lowered.contains("git status") || lowered.contains("what changed") || lowered.contains("show changes"))
            return new Intent("repo", List.of("status"), "inspect repository status");
        Matcher git = GIT_READ.matcher(original);
        if (git.find()) return new Intent("git", List.of(git.group(1).toLowerCase(Locale.ROOT)), "checking Git " + git.group(1));
        if (lowered.contains("install this repo") || lowered.contains("install the repo") || lowered.contains("install myai") || lowered.contains("set up this repo")) {
            List<String> args = new ArrayList<>();
            if (lowered.contains("yes") || lowered.contains("confirm") || lowered.contains("do it")) args.add("--confirm");
            return new Intent("install", args, "install the current repository");
        }
        if (lowered.contains("list tasks") || lowered.contains("show todos") || lowered.contains("show my tasks") || lowered.contains("todo list"))
            return new Intent("todo", List.of("list"), "show the TODO list");

        Matcher m = ADD_TASK.matcher(original);
        if (m.find()) return new Intent("todo", List.of("add", m.group(1).strip()), "add a TODO item");

        m = COMPLETE_TASK.matcher(lowered);
        if (m.find()) return new Intent("todo", List.of("done", m.group(1)), "complete a TODO item");

        m = WALK.matcher(original);
        if (m.find()) {
            String pattern = m.group(1).strip();
            if (!pattern.contains("*") && !pattern.contains("?") && !pattern.contains("[")) {
                pattern = "*." + pattern.replaceFirst("^\\.", "").toLowerCase(Locale.ROOT);
                if (pattern.endsWith(".python")) pattern = "*.py";
            }
            return new Intent("walk", List.of(pattern), "list repository files");
        }

        m = READ_FILE.matcher(original);
        if (m.find()) {
            String path = m.group(1).strip().replaceAll("^['\"]+|['\"]+$", "");
            path = path.split("\\s+and\\s+(?:tell|explain|show)\\b", 2)[0].strip();
            return new Intent("read_file", List.of(path), "read a repository file");
        }

        m = WRITE_FILE.matcher(original);
        if (m.find()) return new Intent("write_file", List.of(m.group(1).strip(), m.group(2).strip().replaceAll("^['\"]+|['\"]+$", "")), "edit a repository file");

        m = HOW_TO.matcher(original);
        if (m.find()) {
            String query = m.group(1) != null ? m.group(1) : m.group(2) != null ? m.group(2) : m.group(3);
            return new Intent("search", List.of(query.strip()), "looking for a local code or documentation example");
        }

        m = SEARCH.matcher(original);
        if (m.find()) return new Intent("search", List.of(m.group(1).strip()), "search local repository help");

        m = LINT.matcher(original);
        if (m.find()) return new Intent("lint", List.of(m.group(1).strip().replaceAll("^['\"]+|['\"]+$", "")), "validate a source file");

        if ("diagnostics".equals(lowered) || "run diagnostics".equals(lowered) || "check the system".equals(lowered))
            return new Intent("diagnostics", List.of(), "run local diagnostics");

        if (lowered.startsWith("commit ") || lowered.contains("make a commit") || lowered.contains("commit this")) {
            List<String> args = new ArrayList<>();
            if (lowered.contains("confirm") || lowered.contains("yes") || lowered.contains("do it")) args.add("--confirm");
            String message = original.split(" ", 2)[1];
            if (message.isBlank()) message = "Update repository";
            args.add(0, message);
            args.add(0, "commit");
            return new Intent("repo", args, "create a guarded repository commit");
        }

        return null;
    }
}
