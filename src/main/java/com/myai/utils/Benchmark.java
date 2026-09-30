package com.myai.utils;

import java.time.Instant;
import java.time.Duration;

public record Benchmark(String name, double seconds, Object result) {
}
