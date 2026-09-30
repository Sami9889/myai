package com.myai.tools;

import com.myai.utils.Validators;

import java.util.Map;

public abstract class BaseTool {
    public String name;
    public String description;

    public abstract Map<String, Object> validate(Map<String, Object> arguments);

    public abstract ToolResult execute(Map<String, Object> arguments);

    public ToolResult run(Map<String, Object> arguments) {
        if (!(arguments instanceof Map)) return new ToolResult(false, "", "arguments must be a JSON object");
        try {
            return execute(validate(arguments));
        } catch (Exception exc) {
            return new ToolResult(false, "", exc.getClass().getName() + ": " + exc.getMessage());
        }
    }

    protected static String string(Map<String, Object> arguments, String name, String defaultValue) {
        Object value = arguments.getOrDefault(name, defaultValue);
        return Validators.requireString(value, name);
    }
}
