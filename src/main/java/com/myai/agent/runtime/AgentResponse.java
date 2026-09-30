package com.myai.agent.runtime;

import java.util.List;

public record AgentResponse(String text, SessionState state, List<ToolResult> toolResults) {
}
