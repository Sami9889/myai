package com.myai.agent.runtime;

import java.util.List;
import com.myai.tools.ToolResult;

public record AgentResponse(String text, SessionState state, List<ToolResult> toolResults) {
}
