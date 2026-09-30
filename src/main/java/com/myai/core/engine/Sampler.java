package com.myai.core.engine;

import java.util.*;
import java.util.function.Function;

public class Sampler {
    public record SamplingConfig(double temperature, int topK, double topP, double repetitionPenalty, Integer seed) {
        public SamplingConfig {
            if (temperature <= 0) temperature = 1e-5;
            if (repetitionPenalty <= 0) repetitionPenalty = 1e-6;
        }

        public SamplingConfig(double temperature, int topK, double topP) {
            this(temperature, topK, topP, 1.1, null);
        }
    }

    private final SamplingConfig config;
    private final Random random;

    public Sampler(SamplingConfig config) {
        this.config = config != null ? config : new SamplingConfig(0.7, 40, 0.9);
        this.random = config.seed() != null ? new Random(config.seed()) : new Random();
    }

    private List<Map.Entry<Integer, Double>> probabilities(List<Double> logits, List<Integer> history) {
        if (logits.isEmpty()) throw new IllegalArgumentException("cannot sample empty logits");
        double temperature = Math.max(1e-5, config.temperature());
        List<Double> adjusted = new ArrayList<>(logits);
        double penalty = Math.max(1e-6, config.repetitionPenalty());
        Set<Integer> seen = new HashSet<>(history);
        for (int token : seen) {
            if (token >= 0 && token < adjusted.size()) {
                double val = adjusted.get(token);
                adjusted.set(token, val > 0 ? val / penalty : val * penalty);
            }
        }
        double maximum = Collections.max(adjusted);
        List<Double> values = new ArrayList<>(adjusted.size());
        double total = 0.0;
        for (double value : adjusted) {
            double v = Math.exp(Math.max(-80.0, Math.min(80.0, value / temperature - maximum / temperature)));
            values.add(v);
            total += v;
        }
        if (total == 0.0) total = 1.0;
        List<Map.Entry<Integer, Double>> ranked = new ArrayList<>();
        for (int i = 0; i < values.size(); i++) {
            ranked.add(Map.entry(i, values.get(i) / total));
        }
        ranked.sort((a, b) -> Double.compare(b.getValue(), a.getValue()));
        if (config.topK() > 0) {
            ranked = ranked.subList(0, Math.min(config.topK(), ranked.size()));
        }
        List<Map.Entry<Integer, Double>> selected = new ArrayList<>();
        double cumulative = 0.0;
        double threshold = Math.min(1.0, Math.max(0.0, config.topP()));
        for (Map.Entry<Integer, Double> item : ranked) {
            selected.add(item);
            cumulative += item.getValue();
            if (cumulative >= threshold) break;
        }
        double normalization = 0.0;
        for (Map.Entry<Integer, Double> item : selected) normalization += item.getValue();
        if (normalization == 0.0) normalization = 1.0;
        List<Map.Entry<Integer, Double>> result = new ArrayList<>(selected.size());
        for (Map.Entry<Integer, Double> item : selected) {
            result.add(Map.entry(item.getKey(), item.getValue() / normalization));
        }
        return result;
    }

    public int sample(List<Double> logits, List<Integer> history) {
        List<Map.Entry<Integer, Double>> probabilities = probabilities(logits, history);
        double target = random.nextDouble();
        double cumulative = 0.0;
        for (Map.Entry<Integer, Double> item : probabilities) {
            cumulative += item.getValue();
            if (target <= cumulative) return item.getKey();
        }
        return probabilities.get(probabilities.size() - 1).getKey();
    }

    public int greedy(List<Double> logits) {
        if (logits.isEmpty()) throw new IllegalArgumentException("cannot choose from empty logits");
        int best = 0;
        for (int i = 1; i < logits.size(); i++) {
            if (logits.get(i) > logits.get(best)) best = i;
        }
        return best;
    }
}
