package com.myai.core.engine;

import java.io.IOException;
import java.nio.file.Path;
import java.util.*;
import java.util.function.BiConsumer;

public class Trainer {
    @FunctionalInterface
    public interface ProgressCallback extends BiConsumer<String, Map<String, Object>> {}

    private static double crossEntropyLoss(List<Double> logits, int target) {
        double maxLogit = Collections.max(logits);
        List<Double> exps = new ArrayList<>(logits.size());
        double total = 0.0;
        for (double x : logits) {
            double v = Math.exp(x - maxLogit);
            exps.add(v);
            total += v;
        }
        double logSum = maxLogit + Math.log(total);
        double loss = -logits.get(target) + logSum;
        List<Double> probs = new ArrayList<>(exps.size());
        for (double x : exps) probs.add(x / total);
        List<Double> grad = new ArrayList<>(probs.size());
        for (int i = 0; i < probs.size(); i++) {
            grad.add(probs.get(i) - (i == target ? 1.0 : 0.0));
        }
        return loss;
    }

    private static void clipGradients(List<Double> data, double maxNorm) {
        double total = 0.0;
        for (double x : data) total += x * x;
        double norm = Math.sqrt(total);
        if (norm > maxNorm) {
            double scale = maxNorm / norm;
            for (int i = 0; i < data.size(); i++) {
                data.set(i, data.get(i) * scale);
            }
        }
    }

    private static void updateWeight(List<Double> data, List<Double> grad, double lr) {
        for (int i = 0; i < data.size(); i++) {
            double val = data.get(i) - lr * grad.get(i);
            if (Double.isFinite(val)) {
                data.set(i, Math.max(-10.0, Math.min(10.0, val)));
            } else {
                data.set(i, 0.0);
            }
        }
    }

    public static double trainStep(Transformer.DecoderTransformer transformer, Tokenizer tokenizer, List<Integer> tokens, double lr) {
        int ctx = transformer.config.contextLength();
        double totalLoss = 0.0;
        int count = 0;

        Tensor embeddings = transformer.embeddings();
        List<Transformer.TransformerBlock> blocks = transformer.blocks();
        Transformer.RMSNorm finalNorm = transformer.finalNorm();
        Transformer.Linear output = transformer.output();

        for (int step = 0; step < tokens.size() - 1; step++) {
            int start = Math.max(0, step + 1 - ctx);
            List<Integer> chunk = tokens.subList(start, step + 1);
            int target = tokens.get(step + 1);

            List<List<Double>> sequence = new ArrayList<>(chunk.size());
            for (int t : chunk) {
                sequence.add(embeddings.row(t));
            }
            for (Transformer.TransformerBlock block : blocks) {
                List<List<Double>> normalized = new ArrayList<>(sequence.size());
                for (List<Double> row : sequence) {
                    normalized.add(block.attentionNorm().apply(row));
                }
                List<List<Double>> attention = block.attention().apply(normalized);
                List<List<Double>> residual = new ArrayList<>(sequence.size());
                for (int i = 0; i < sequence.size(); i++) {
                    List<Double> row = sequence.get(i);
                    List<Double> update = attention.get(i);
                    List<Double> combined = new ArrayList<>(row.size());
                    for (int j = 0; j < row.size(); j++) combined.add(row.get(j) + update.get(j));
                    residual.add(combined);
                }
                sequence = new ArrayList<>(residual.size());
                for (List<Double> row : residual) {
                    List<Double> ffnOut = block.feedForward().apply(block.feedForwardNorm().apply(row));
                    List<Double> combined = new ArrayList<>(row.size());
                    for (int j = 0; j < row.size(); j++) combined.add(row.get(j) + ffnOut.get(j));
                    sequence.add(combined);
                }
            }
            List<Double> hidden = finalNorm.apply(sequence.get(sequence.size() - 1));
            List<Double> logits = output.apply(hidden);

            double loss = crossEntropyLoss(logits, target);
            totalLoss += loss;
            count++;

            List<Double> grad = new ArrayList<>(logits.size());
            for (int i = 0; i < logits.size(); i++) {
                grad.add(logits.get(i) - (i == target ? 1.0 : 0.0));
            }

            clipGradients(grad, 1.0);
            for (int i = 0; i < output.weight.shape().value()[0]; i++) {
                for (int j = 0; j < output.weight.shape().value()[1]; j++) {
                    int idx = i * output.weight.shape().value()[1] + j;
                    output.weight.data().set(idx, output.weight.data().get(idx) - lr * grad.get(i) * hidden.get(j));
                    double val = output.weight.data().get(idx);
                    if (Double.isFinite(val)) {
                        output.weight.data().set(idx, Math.max(-10.0, Math.min(10.0, val)));
                    } else {
                        output.weight.data().set(idx, 0.0);
                    }
                }
            }
            if (output.bias != null) {
                for (int i = 0; i < grad.size(); i++) {
                    output.bias.data().set(i, output.bias.data().get(i) - lr * grad.get(i));
                    double val = output.bias.data().get(i);
                    if (Double.isFinite(val)) {
                        output.bias.data().set(i, Math.max(-10.0, Math.min(10.0, val)));
                    } else {
                        output.bias.data().set(i, 0.0);
                    }
                }
            }

            List<Double> hiddenGrad = new ArrayList<>(hidden.size());
            for (int i = 0; i < hidden.size(); i++) hiddenGrad.add(0.0);
            for (int i = 0; i < hidden.size(); i++) {
                for (int j = 0; j < grad.size(); j++) {
                    hiddenGrad.set(i, hiddenGrad.get(i) + grad.get(j) * output.weight.data().get(j * output.weight.shape().value()[1] + i));
                }
            }

            for (int i = 0; i < hiddenGrad.size(); i++) {
                for (int j = 0; j < sequence.get(sequence.size() - 1).size(); j++) {
                    int idx = chunk.get(chunk.size() - 1) * embeddings.shape().value()[1] + j;
                    double val = embeddings.data().get(idx) - lr * hiddenGrad.get(i) * sequence.get(sequence.size() - 1).get(j);
                    if (Double.isFinite(val)) {
                        embeddings.data().set(idx, Math.max(-10.0, Math.min(10.0, val)));
                    } else {
                        embeddings.data().set(idx, 0.0);
                    }
                }
            }
        }
        return totalLoss / Math.max(1, count);
    }

    public static void trainOnText(Path modelPath, Tokenizer tokenizer, List<String> texts, int epochs, double lr, Long seed, ProgressCallback progressCallback) {
        Map<String, Tensor> records;
        try (WeightFile wf = new WeightFile(modelPath)) {
            records = new LinkedHashMap<>();
            for (String name : wf.names()) {
                records.put(name, wf.read(name));
            }
        } catch (IOException e) {
            throw new RuntimeException("Failed to load model: " + e.getMessage(), e);
        }

        Transformer.DecoderTransformer transformer = buildTransformerFromRecords(records, tokenizer);

        for (int epoch = 0; epoch < epochs; epoch++) {
            List<String> shuffled = new ArrayList<>(texts);
            Collections.shuffle(shuffled, seed != null ? new Random(seed + epoch) : new Random());
            double epochLoss = 0.0;
            int steps = 0;
            long epochStart = System.currentTimeMillis();

            Map<String, Object> startKwargs = new LinkedHashMap<>();
            startKwargs.put("epoch", epoch + 1);
            startKwargs.put("epochs", epochs);
            startKwargs.put("total_texts", texts.size());
            if (progressCallback != null) progressCallback.accept("epoch_start", startKwargs);

            for (int textIndex = 0; textIndex < shuffled.size(); textIndex++) {
                String text = shuffled.get(textIndex);
                List<Integer> tokenIds = tokenizer.encode(text);
                if (tokenIds.size() < 2) continue;
                long stepStart = System.currentTimeMillis();
                double loss = trainStep(transformer, tokenizer, tokenIds, lr);
                long stepElapsed = System.currentTimeMillis() - stepStart;
                epochLoss += loss;
                steps++;

                Map<String, Object> stepKwargs = new LinkedHashMap<>();
                stepKwargs.put("epoch", epoch + 1);
                stepKwargs.put("epochs", epochs);
                stepKwargs.put("text_index", textIndex + 1);
                stepKwargs.put("total_texts", shuffled.size());
                stepKwargs.put("loss", loss);
                stepKwargs.put("step_time", stepElapsed / 1000.0);
                stepKwargs.put("avg_step_time", stepElapsed / 1000.0);
                if (progressCallback != null) progressCallback.accept("step", stepKwargs);
            }
            double avg = epochLoss / Math.max(1, steps);
            long epochElapsed = System.currentTimeMillis() - epochStart;

            Map<String, Object> endKwargs = new LinkedHashMap<>();
            endKwargs.put("epoch", epoch + 1);
            endKwargs.put("epochs", epochs);
            endKwargs.put("loss", avg);
            endKwargs.put("elapsed", epochElapsed / 1000.0);
            endKwargs.put("steps", steps);
            if (progressCallback != null) progressCallback.accept("epoch_end", endKwargs);
        }

        try {
            WeightsParser.writeWeights(modelPath, records);
        } catch (IOException e) {
            throw new RuntimeException("Failed to write weights: " + e.getMessage(), e);
        }
    }

    private static Transformer.DecoderTransformer buildTransformerFromRecords(Map<String, Tensor> records, Tokenizer tokenizer) {
        int vocabSize = tokenizer.vocabularySize();
        int ctx = 64;
        int hidden = 8;
        int layers = 1;
        int heads = 2;

        Tensor embeddings = first(records, "tok_embeddings", "embeddings", "word_embeddings");
        Tensor finalNormData = first(records, "final_norm", "ln_f", "layer_norm");
        Transformer.RMSNorm finalNorm = new Transformer.RMSNorm(finalNormData.data());
        Tensor outputWeight = first(records, "lm_head", "output", "word_embeddings");
        Transformer.Linear output = new Transformer.Linear(outputWeight);

        List<Transformer.TransformerBlock> blocks = new ArrayList<>();
        for (int i = 0; i < layers; i++) {
            String p = "layers." + i;
            Tensor q = first(records, p + ".attention.query_proj", p + ".query", p + ".attn.q_proj");
            Tensor k = first(records, p + ".attention.key_proj", p + ".key", p + ".attn.k_proj");
            Tensor v = first(records, p + ".attention.value_proj", p + ".value", p + ".attn.v_proj");
            Tensor o = first(records, p + ".attention.output_proj", p + ".output", p + ".attn.o_proj");
            Transformer.CausalSelfAttention attention = new Transformer.CausalSelfAttention(new Transformer.Linear(q), new Transformer.Linear(k), new Transformer.Linear(v), new Transformer.Linear(o), heads, 10000.0);

            Tensor up = first(records, p + ".feed_forward.w1", p + ".up_proj", p + ".mlp.gate_proj");
            Tensor down = first(records, p + ".feed_forward.w2", p + ".down_proj", p + ".mlp.down_proj");
            Transformer.FeedForward feedForward = new Transformer.FeedForward(new Transformer.Linear(up), new Transformer.Linear(down));

            Tensor attnNorm = first(records, p + ".attention_norm", p + ".ln1", p + ".ln_attn");
            Tensor ffnNorm = first(records, p + ".feed_forward_norm", p + ".ln2", p + ".ln_mlp");
            blocks.add(new Transformer.TransformerBlock(attention, feedForward, new Transformer.RMSNorm(attnNorm.data()), new Transformer.RMSNorm(ffnNorm.data())));
        }

        Transformer.TransformerConfig config = new Transformer.TransformerConfig(vocabSize, ctx, hidden, layers, heads, hidden * 4);
        return new Transformer.DecoderTransformer(config, embeddings, blocks, finalNorm, output);
    }

    private static Tensor first(Map<String, Tensor> records, String... names) {
        for (String name : names) {
            if (records.containsKey(name)) return records.get(name);
        }
        return null;
    }
}
