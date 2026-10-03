package com.myai.tools;

import com.myai.core.engine.Tensor;
import com.myai.core.engine.Tokenizer;
import com.myai.core.engine.WeightsParser;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

public class GenerateModel {
    public static void main(String[] args) throws IOException {
        Path root = Path.of("").toAbsolutePath().normalize();
        Path modelDir = root.resolve("models");
        Files.createDirectories(modelDir);

        Map<String, Integer> vocab = new LinkedHashMap<>();
        for (int i = 0; i < 256; i++) vocab.put(String.valueOf((char) i), i);
        vocab.put("<unk>", 256);
        vocab.put("<eos>", 257);

        Tokenizer tokenizer = new Tokenizer(vocab, List.of());
        Map<String, Object> tokenizerJson = new LinkedHashMap<>();
        tokenizerJson.put("vocab", vocab);
        tokenizerJson.put("merges", List.of());
        String tokenizerStr = mapToJson(tokenizerJson);
        Files.writeString(modelDir.resolve("tokenizer.json"), tokenizerStr);

        int hiddenSize = 8;
        int vocabSize = vocab.size();
        int layers = 1;
        int heads = 2;
        int contextLength = 16;

        Random random = new Random(42);
        Map<String, Tensor> weights = new LinkedHashMap<>();
        weights.put("tok_embeddings", randTensor(new int[]{vocabSize, hiddenSize}, 0.02, random));
        weights.put("final_norm", new Tensor(new Tensor.Shape(new int[]{hiddenSize}), fillList(hiddenSize, 1.0)));
        weights.put("lm_head", randTensor(new int[]{vocabSize, hiddenSize}, 0.02, random));

        for (int i = 0; i < layers; i++) {
            String p = "layers." + i;
            weights.put(p + ".attention.query_proj", randTensor(new int[]{hiddenSize, hiddenSize}, 0.02, random));
            weights.put(p + ".attention.key_proj", randTensor(new int[]{hiddenSize, hiddenSize}, 0.02, random));
            weights.put(p + ".attention.value_proj", randTensor(new int[]{hiddenSize, hiddenSize}, 0.02, random));
            weights.put(p + ".attention.output_proj", randTensor(new int[]{hiddenSize, hiddenSize}, 0.02, random));
            weights.put(p + ".feed_forward.w1", randTensor(new int[]{hiddenSize * 4, hiddenSize}, 0.02, random));
            weights.put(p + ".feed_forward.w2", randTensor(new int[]{hiddenSize, hiddenSize * 4}, 0.02, random));
            weights.put(p + ".attention_norm", new Tensor(new Tensor.Shape(new int[]{hiddenSize}), fillList(hiddenSize, 1.0)));
            weights.put(p + ".feed_forward_norm", new Tensor(new Tensor.Shape(new int[]{hiddenSize}), fillList(hiddenSize, 1.0)));
        }

        Path weightsPath = modelDir.resolve("local_model.bin");
        WeightsParser.writeWeights(weightsPath, weights);

        Map<String, Object> config = new LinkedHashMap<>();
        Map<String, Object> modelCfg = new LinkedHashMap<>();
        modelCfg.put("path", "models/local_model.bin");
        modelCfg.put("tokenizer", "models/tokenizer.json");
        modelCfg.put("context_length", contextLength);
        modelCfg.put("hidden_size", hiddenSize);
        modelCfg.put("layers", layers);
        modelCfg.put("heads", heads);
        config.put("model", modelCfg);
        Map<String, Object> runtime = new LinkedHashMap<>();
        runtime.put("max_steps", 32);
        runtime.put("temperature", 0.7);
        runtime.put("top_k", 40);
        runtime.put("top_p", 0.9);
        config.put("runtime", runtime);
        Map<String, Object> security = new LinkedHashMap<>();
        security.put("confirm_shell", true);
        security.put("allow_network", true);
        security.put("workspace", ".");
        config.put("security", security);
        List<String> prompts = List.of(
            "write a Python function to sort a list", "implement a linked list in Python",
            "create a REST API endpoint in Flask", "write a Dockerfile for a Python app",
            "refactor this function for readability", "add type hints to this module",
            "write unit tests for this class", "optimize this SQL query",
            "implement a binary search algorithm", "create a React component for a todo list",
            "write a shell script to backup a database", "implement a retry decorator with exponential backoff",
            "create a middleware for authentication", "write a CSV parser with error handling",
            "implement a priority queue using a heap"
        );
        config.put("coding_prompts", prompts);
        Files.writeString(root.resolve("config.json"), mapToJson(config));

        System.out.println("Created model: " + weightsPath);
        System.out.println("Created tokenizer: " + modelDir.resolve("tokenizer.json"));
        System.out.println("Updated config: " + root.resolve("config.json"));
    }

    private static Tensor randTensor(int[] shape, double scale, Random random) {
        int size = 1;
        for (int d : shape) size *= d;
        List<Double> data = new ArrayList<>(size);
        for (int i = 0; i < size; i++) data.add(random.nextDouble(-scale, scale));
        return new Tensor(new Tensor.Shape(shape), data);
    }

    private static List<Double> fillList(int n, double v) {
        List<Double> list = new ArrayList<>(n);
        for (int i = 0; i < n; i++) list.add(v);
        return list;
    }

    private static String mapToJson(Map<String, Object> map) {
        StringBuilder sb = new StringBuilder("{\n");
        int count = 0;
        for (Map.Entry<String, Object> entry : map.entrySet()) {
            if (count++ > 0) sb.append(",\n");
            sb.append("  \"").append(entry.getKey()).append("\": ").append(valueToJson(entry.getValue()));
        }
        sb.append("\n}\n");
        return sb.toString();
    }

    private static String valueToJson(Object value) {
        if (value instanceof String s) return "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
        if (value instanceof Number n) return String.valueOf(n);
        if (value instanceof Boolean b) return String.valueOf(b);
        if (value instanceof List<?> list) {
            StringBuilder sb = new StringBuilder("[");
            for (int i = 0; i < list.size(); i++) {
                if (i > 0) sb.append(", ");
                sb.append(valueToJson(list.get(i)));
            }
            return sb.append("]").toString();
        }
        if (value instanceof Map<?, ?> map) {
            StringBuilder sb = new StringBuilder("{");
            int c = 0;
            for (Map.Entry<?, ?> e : map.entrySet()) {
                if (c++ > 0) sb.append(", ");
                sb.append("\"").append(e.getKey()).append("\": ").append(valueToJson(e.getValue()));
            }
            return sb.append("}").toString();
        }
        return String.valueOf(value);
    }
}
