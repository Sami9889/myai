package com.myai.utils;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public record GateDecision(boolean allowed, String reason, boolean requiresConfirmation) {
}
