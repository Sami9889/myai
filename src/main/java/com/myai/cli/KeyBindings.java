package com.myai.cli;

import java.util.*;

public class KeyBindings {
    private boolean multiline;

    public boolean multiline() { return multiline; }

    public String handle(String line) {
        String command = line.strip();
        if (command.equals("/quit") || command.equals("/exit")) return "quit";
        if (command.equals("/multiline")) {
            multiline = !multiline;
            return "multiline";
        }
        return null;
    }
}
