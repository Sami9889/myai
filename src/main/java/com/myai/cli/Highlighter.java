package com.myai.cli;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class Highlighter {
    private static final Set<String> KEYWORDS = Set.of(
        "def", "class", "return", "if", "else", "elif", "for", "while", "in",
        "import", "from", "as", "True", "False", "None", "try", "except", "with", "yield"
    );

    public String highlight(String text) {
        for (String keyword : KEYWORDS) {
            text = text.replaceAll("\\b" + keyword + "\\b", "\033[35m" + keyword + "\033[0m");
        }
        text = text.replaceAll("(\"[^\"\\\\]*(?:\\\\.[^\"\\\\]*)*\"|'[^'\\\\]*(?:\\\\.[^'\\\\]*)*')", "\033[32m$1\033[0m");
        return text;
    }
}
