package com.myai.cli;

import java.util.concurrent.atomic.AtomicBoolean;

public class Spinner {
    private final String label;
    private final char[] frames = {'|', '/', '-', '\\'};
    private int frameIndex;
    private AtomicBoolean active;

    public Spinner(String label) {
        this.label = label;
        this.frameIndex = 0;
        this.active = new AtomicBoolean(false);
    }

    public void start() { active.set(true); }
    public void stop() {
        if (active.getAndSet(false)) {
            System.err.print("\r" + " ".repeat(label.length() + 4) + "\r");
            System.err.flush();
        }
    }
}
