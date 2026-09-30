package com.myai.utils;

import java.util.logging.*;

public class Logger {
    public static java.util.logging.Logger getLogger(String name, String path) {
        java.util.logging.Logger logger = java.util.logging.Logger.getLogger(name);
        if (logger.getHandlers().length > 0) return logger;
        logger.setLevel(java.util.logging.Level.INFO);
        Handler handler;
        if (path != null && !path.isEmpty()) {
            try {
                handler = new FileHandler(path);
            } catch (Exception e) {
                handler = new ConsoleHandler();
            }
        } else {
            handler = new ConsoleHandler();
        }
        handler.setFormatter(new Formatter() {
            @Override
            public String format(LogRecord record) {
                return String.format("%s %s %s: %s%n",
                    java.time.Instant.ofEpochMilli(record.getMillis()).toString(),
                    record.getLevel().getName(),
                    record.getLoggerName(),
                    record.getMessage());
            }
        });
        logger.addHandler(handler);
        return logger;
    }

    public static java.util.logging.Logger getLogger(String name) {
        return getLogger(name, null);
    }
}
