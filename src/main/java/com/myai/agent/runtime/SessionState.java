package com.myai.agent.runtime;

import java.time.Instant;
import java.util.*;

public class SessionState {
    private SessionStatus status;
    private int step;
    private String task;
    private List<String> events;
    private List<String> errors;
    private long started;

    public SessionState() {
        this(SessionStatus.IDLE, 0, "", new ArrayList<>(), new ArrayList<>(), Instant.now().toEpochMilli());
    }

    public SessionState(SessionStatus status, int step, String task, List<String> events, List<String> errors, long started) {
        this.status = status;
        this.step = step;
        this.task = task;
        this.events = events;
        this.errors = errors;
        this.started = started;
    }

    public SessionState(String task) {
        this(SessionStatus.IDLE, 0, task, new ArrayList<>(), new ArrayList<>(), Instant.now().toEpochMilli());
    }

    public SessionStatus status() { return status; }
    public int step() { return step; }
    public String task() { return task; }
    public List<String> events() { return events; }
    public List<String> errors() { return errors; }
    public long started() { return started; }

    public void transition(SessionStatus status, String message) {
        this.status = status;
        this.step++;
        if (message != null && !message.isEmpty()) this.events.add(message);
    }

    public void fail(String message) {
        this.errors.add(message);
        transition(SessionStatus.FAILED, message);
    }

    public Map<String, Object> snapshot() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("status", status.name());
        m.put("step", step);
        m.put("task", task);
        m.put("events", events.size());
        m.put("errors", errors.size());
        m.put("age_seconds", (Instant.now().toEpochMilli() - started) / 1000.0);
        return m;
    }
}
