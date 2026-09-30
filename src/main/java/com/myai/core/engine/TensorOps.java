package com.myai.core.engine;

import java.util.*;
import java.util.function.Function;

public class TensorOps {
    public static double dot(List<Double> left, List<Double> right) {
        if (left.size() != right.size()) throw new IllegalArgumentException("vector shape mismatch");
        double sum = 0.0;
        for (int i = 0; i < left.size(); i++) sum += left.get(i) * right.get(i);
        return sum;
    }

    public static double cosineSimilarity(List<Double> left, List<Double> right) {
        double denominator = Math.sqrt(dot(left, left) * dot(right, right));
        return denominator == 0.0 ? 0.0 : dot(left, right) / denominator;
    }

    public static double rms(List<Double> values, double epsilon) {
        double sum = 0.0;
        for (double v : values) sum += v * v;
        return Math.sqrt(sum / Math.max(1, values.size()) + epsilon);
    }

    public static List<Double> softmax(List<Double> values) {
        double maximum = values.get(0);
        for (double v : values) if (v > maximum) maximum = v;
        List<Double> exps = new ArrayList<>(values.size());
        double total = 0.0;
        for (double x : values) {
            double v = Math.exp(Math.max(-80.0, Math.min(80.0, x - maximum)));
            exps.add(v);
            total += v;
        }
        if (total == 0.0) total = 1.0;
        List<Double> result = new ArrayList<>(exps.size());
        for (double v : exps) result.add(v / total);
        return result;
    }

    public static double[][] matmul(double[][] left, double[][] right) {
        int rows = left.length;
        int inner = left[0].length;
        int cols = right[0].length;
        double[][] result = new double[rows][cols];
        for (int row = 0; row < rows; row++) {
            for (int pivot = 0; pivot < inner; pivot++) {
                double coefficient = left[row][pivot];
                for (int col = 0; col < cols; col++) {
                    result[row][col] += coefficient * right[pivot][col];
                }
            }
        }
        return result;
    }
}
