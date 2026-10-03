package com.myai.utils;

import java.time.Instant;
import java.time.Duration;

public class Benchmarker {
    public static Benchmark measure(String name, java.util.concurrent.Callable<Object> function) {
        try {
            Instant start = Instant.now();
            Object result = function.call();
            double seconds = Duration.between(start, Instant.now()).toMillis() / 1000.0;
            return new Benchmark(name, seconds, result);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
