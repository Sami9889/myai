package com.myai.tools;

import com.myai.core.engine.Tokenizer;
import com.myai.core.engine.Trainer;
import com.myai.utils.ConfigLoader;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.stream.Stream;

public class TrainModel {
    public static void main(String[] args) throws Exception {
        train(Path.of(""));
    }

    public static void train(Path workspace) throws Exception {
        Path root = workspace.toAbsolutePath().normalize();
        Map<String, Object> config = ConfigLoader.loadConfig(root.resolve("config.json").toString());
        Map<String, Object> modelCfg = (Map<String, Object>) config.getOrDefault("model", Map.of());
        Path modelPath = root.resolve((String) modelCfg.getOrDefault("path", "models/local_model.bin")).normalize();
        Path tokenizerPath = root.resolve((String) modelCfg.getOrDefault("tokenizer", "models/tokenizer.json")).normalize();
        if (!modelPath.startsWith(root) || !tokenizerPath.startsWith(root)) throw new IllegalArgumentException("model paths must stay inside the workspace");
        Path corpusPath = root.resolve((String) config.getOrDefault("training_corpus", ".")).normalize();
        if (!corpusPath.startsWith(root)) throw new IllegalArgumentException("training corpus must stay inside the workspace");
        if (!Files.isDirectory(corpusPath)) throw new IllegalArgumentException("local training corpus not found: " + corpusPath);
        int epochs = 3;
        double lr = 0.005;
        int maxChars = 20000;

        Tokenizer tokenizer = Tokenizer.fromJson(tokenizerPath.toString());
        System.out.println("[tokenizer] loaded vocab_size=" + tokenizer.vocabularySize());

        List<String> texts = new ArrayList<>();
        int charsRead = 0;
        try (Stream<Path> files = Files.walk(corpusPath)) {
            for (Path file : files.filter(Files::isRegularFile).filter(TrainModel::isRelevantCorpusFile).sorted().toList()) {
                String filename = file.getFileName().toString().toLowerCase(Locale.ROOT);
                if (!(filename.endsWith(".txt") || filename.endsWith(".md")
                    || filename.endsWith(".java") || filename.endsWith(".py"))) continue;
                if (charsRead >= maxChars || Files.size(file) > maxChars) continue;
                String content = Files.readString(file);
                int remaining = maxChars - charsRead;
                if (content.length() > remaining) content = content.substring(0, remaining);
                charsRead += content.length();
                for (String section : content.split("\\R\\s*\\R")) {
                    if (section.strip().length() > 10) texts.add(section);
                }
            }
        }
        if (texts.isEmpty()) throw new IllegalArgumentException("no usable local .txt, .md, .java, or .py files in " + corpusPath);
        System.out.println("[data] loaded " + charsRead + " local characters from " + corpusPath);
        System.out.println("[data] training sections=" + texts.size());

        System.out.println("[train] starting");
        long trainStart = System.currentTimeMillis();
        Trainer.trainOnText(modelPath, tokenizer, texts, epochs, lr, 42L, (event, kwargs) -> {
            switch (event) {
                case "epoch_start" -> {
                    int epoch = (Integer) kwargs.get("epoch");
                    int epochsTotal = (Integer) kwargs.get("epochs");
                    int totalTexts = (Integer) kwargs.get("total_texts");
                    System.out.println("=".repeat(72));
                    System.out.println("[train] epoch " + epoch + "/" + epochsTotal + " started | texts=" + totalTexts);
                    System.out.println("=".repeat(72));
                }
                case "step" -> {
                    int epoch = (Integer) kwargs.get("epoch");
                    int epochsTotal = (Integer) kwargs.get("epochs");
                    int textIndex = (Integer) kwargs.get("text_index");
                    int totalTexts = (Integer) kwargs.get("total_texts");
                    double loss = (Double) kwargs.get("loss");
                    double stepTime = (Double) kwargs.get("step_time");
                    double avgStep = (Double) kwargs.get("avg_step_time");
                    double pct = textIndex / (double) totalTexts * 100;
                    System.out.printf("  [train] epoch=%d/%d step=%d/%d (%.0f%%) loss=%.4f step=%.2fs avg=%.2fs%n",
                        epoch, epochsTotal, textIndex, totalTexts, pct, loss, stepTime, avgStep);
                }
                case "epoch_end" -> {
                    int epoch = (Integer) kwargs.get("epoch");
                    int epochsTotal = (Integer) kwargs.get("epochs");
                    double loss = (Double) kwargs.get("loss");
                    double elapsed = (Double) kwargs.get("elapsed");
                    int steps = (Integer) kwargs.get("steps");
                    System.out.println("=".repeat(72));
                    System.out.printf("[train] epoch=%d/%d complete | loss=%.4f | steps=%d | time=%.1fs%n", epoch, epochsTotal, loss, steps, elapsed);
                    System.out.println("=".repeat(72));
                }
            }
        });

        long trainElapsed = System.currentTimeMillis() - trainStart;
        System.out.println("[train] completed in " + (trainElapsed / 1000.0) + "s");
        System.out.println("[model] saved to: " + modelPath);
    }

    private static boolean isRelevantCorpusFile(Path file) {
        for (Path part : file) {
            String name = part.toString();
            if (Set.of(".git", ".venv", "target", "build", "dist", "models", "node_modules").contains(name)) return false;
        }
        return true;
    }
}
