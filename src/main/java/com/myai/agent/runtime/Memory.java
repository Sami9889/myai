package com.myai.agent.runtime;

import java.util.List;

public record Memory(String text, List<Double> vector, java.util.Map<String, String> metadata) {
}
