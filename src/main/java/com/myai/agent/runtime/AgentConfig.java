package com.myai.agent.runtime;

public record AgentConfig(int maxSteps, int maxContextTokens, int maxRepeatedActions) {
    public AgentConfig() {
        this(32, 2048, 3);
    }
}
