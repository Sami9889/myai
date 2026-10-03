package com.myai.tools;

import java.lang.management.ManagementFactory;
import java.lang.management.OperatingSystemMXBean;
import java.util.Map;

public class SystemDiagnostics extends BaseTool {
    public String name() { return "diagnostics"; }
    public String description() { return "Report local runtime and resource information."; }

    @Override
    public Map<String, Object> validate(Map<String, Object> arguments) {
        return Map.of();
    }

    @Override
    public ToolResult execute(Map<String, Object> arguments) throws Exception {
        OperatingSystemMXBean os = ManagementFactory.getOperatingSystemMXBean();
        String platform = System.getProperty("os.name") + " " + System.getProperty("os.version");
        String javaVersion = System.getProperty("java.version");
        int cpus = Runtime.getRuntime().availableProcessors();
        long memory = Runtime.getRuntime().maxMemory() / (1024 * 1024);
        String text = "platform=" + platform + "\njava=" + javaVersion + "\ncpus=" + cpus + "\nmax_memory_mb=" + memory;
        return new ToolResult(true, text, null);
    }
}
