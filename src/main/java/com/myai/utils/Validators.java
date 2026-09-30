package com.myai.utils;

import java.nio.file.Path;

public class Validators {
    public static String requireString(Object value, String name) {
        if (!(value instanceof String str) || str.trim().isEmpty()) {
            throw new ValidationError(name + " must be a non-empty string");
        }
        return str;
    }

    public static int requireInt(Object value, String name, Integer minimum) {
        if (value instanceof Boolean || !(value instanceof Integer integer)) {
            throw new ValidationError(name + " must be an integer");
        }
        if (minimum != null && integer < minimum) {
            throw new ValidationError(name + " must be >= " + minimum);
        }
        return integer;
    }

    public static Path confinedPath(String value, String root) {
        Path candidate = Path.of(value).toAbsolutePath().normalize();
        Path base = Path.of(root).toAbsolutePath().normalize();
        if (!candidate.startsWith(base)) {
            throw new ValidationError("path escapes workspace");
        }
        return candidate;
    }
}
