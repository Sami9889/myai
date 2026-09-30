package com.myai.tools;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

public class TrainModel {
    private static final List<String> DEFAULT_QUERIES = List.of(
        "Python programming language", "artificial intelligence", "machine learning",
        "software engineering", "data structures algorithms", "web development", "computer science"
    );

    public static void main(String[] args) throws Exception {
        Path root = Path.of("").toAbsolutePath().normalize();
        Map<String, Object> config = ConfigLoader.loadConfig(root.resolve("config.json").toString());
        Map<String, Object> modelCfg = (Map<String, Object>) config.getOrDefault("model", Map.of());
        Path modelPath = root.resolve((String) modelCfg.getOrDefault("path", "models/local_model.bin"));
        Path tokenizerPath = root.resolve((String) modelCfg.getOrDefault("tokenizer", "models/tokenizer.json"));

        List<String> queries = DEFAULT_QUERIES;
        int epochs = 5;
        double lr = 0.05;
        int maxChars = 20000;
        int timeLimitMinutes = 120;

        Tokenizer tokenizer = Tokenizer.fromJson(tokenizerPath.toString());
        System.out.println("[tokenizer] loaded vocab_size=" + tokenizer.vocabularySize());

        String text = fetchTrainingText(queries, maxChars);
        System.out.println("[data] fetched " + text.length() + " chars");

        if (text.isEmpty()) {
            List<String> fallback = new ArrayList<>();
            for (int i = 0; i < 50; i++) {
                fallback.add("Python is a programming language.");
                fallback.add("Machine learning is a subset of artificial intelligence.");
                fallback.add("Software engineering involves designing and building software.");
                fallback.add("Data structures include arrays, lists, trees, and graphs.");
                fallback.add("Algorithms are step-by-step procedures for solving problems.");
                fallback.add("Web development uses HTML, CSS, and JavaScript.");
                fallback.add("Computer science studies computation and information.");
            }
            text = String.join("\n", fallback);
        }

        List<String> texts = new ArrayList<>();
        for (String t : text.split("\n\n")) {
            if (t.strip().length() > 10) texts.add(t);
        }
        System.out.println("[data] training texts=" + texts.size());

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

    private static String fetchTrainingText(List<String> queries, int maxChars) {
        List<String> parts = new ArrayList<>();
        for (String query : queries) {
            if (parts.stream().mapToInt(String::length).sum() >= maxChars) break;
            try {
                String text = fetchWebText(query, maxChars / queries.size());
                if (!text.isEmpty()) parts.add(text);
            } catch (Exception e) {
                // skip failed source
            }
        }
        return String.join("\n\n", parts);
    }

    private static String fetchWebText(String query, int maxChars) {
        try {
            String url = "https://www.bing.com/search?q=" + java.net.URLEncoder.encode(query, "UTF-8");
            HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
            conn.setRequestProperty("User-Agent", "Mozilla/5.0");
            try (var in = new java.io.InputStreamReader(conn.getInputStream())) {
                StringBuilder sb = new StringBuilder();
                char[] buf = new char[4096];
                int len;
                while ((len = in.read(buf)) >= 0) sb.append(buf, 0, len);
                String html = sb.toString();
                StringBuilder text = new StringBuilder();
                Pattern tagPattern = Pattern.compile("<(script|style|nav|header|footer|aside)[^>]*>.*?</(script|style|nav|header|footer|aside)>", Pattern.DOTALL | Pattern.CASE_INSENSITIVE);
                html = tagPattern.matcher(html).replaceAll("");
                Matcher m = Pattern.compile(">([^<]+)<").matcher(html);
                while (m.find()) {
                    String content = m.group(1).trim();
                    if (!content.isEmpty()) text.append(content).append("\n");
                }
                return text.toString().replaceAll("\\n{3,}", "\n\n").trim();
            }
        } catch (Exception e) {
            return "";
        }
    }
}
