package com.myai.utils;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class ConfigLoader {
    public static Map<String, Object> loadConfig(String path) {
        Path p = Path.of(path);
        if (!Files.exists(p)) return Map.of();
        try {
            String content = Files.readString(p);
            return parseJsonObject(content);
        } catch (IOException e) {
            return Map.of();
        }
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> parseJsonObject(String s) {
        Map<String, Object> result = new LinkedHashMap<>();
        s = s.trim();
        if (!s.startsWith("{") || !s.endsWith("}")) return result;
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
        if (!s.startsWith("[") || !s.endsWith("]")) return list;
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
