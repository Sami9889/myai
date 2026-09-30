package com.myai.utils;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class SecurityGates {
    private static final List<Pattern> DANGEROUS = List.of(
        Pattern.compile("(^|\\s)rm\\s+(-[^ ]*\\s+)*-r"),
        Pattern.compile("git\\s+push\\s+[^\\n]*--force"),
        Pattern.compile("(^|\\s)mkfs(\\s|$)"),
        Pattern.compile("(^|\\s)dd\\s+")
    );

    public static GateDecision inspectCommand(String command) {
        for (Pattern pattern : DANGEROUS) {
            if (pattern.matcher(command).find()) {
                return new GateDecision(false, "dangerous command requires explicit confirmation", true);
            }
        }
        if (Pattern.compile("\\b(curl|wget|nc|netcat)\\b").matcher(command).find()) {
            return new GateDecision(false, "network-capable commands are disabled by default", true);
        }
        return new GateDecision(true, "command is within the default policy", false);
    }

    public static void requireConfirmation(String command, java.util.function.BiFunction<String, String, Boolean> confirmer) {
        GateDecision decision = inspectCommand(command);
        if (decision.requiresConfirmation() && !confirmer.apply(command, decision.reason())) {
            throw new SecurityError("operation rejected by confirmation gate");
        }
        if (!decision.allowed() && !decision.requiresConfirmation()) {
            throw new SecurityError(decision.reason());
        }
    }
}
