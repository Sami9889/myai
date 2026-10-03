package com.myai.core.engine;

import java.util.*;
import java.util.function.Function;

public class Transformer {
    public record TransformerConfig(int vocabularySize, int contextLength, int hiddenSize, int layers, int heads, int intermediateSize, double ropeBase, double epsilon) {
        public TransformerConfig(int vocabularySize, int contextLength, int hiddenSize, int layers, int heads, int intermediateSize) {
            this(vocabularySize, contextLength, hiddenSize, layers, heads, intermediateSize, 10000.0, 1e-6);
        }
    }

    public static class Linear {
        private final Tensor weight;
        private final Tensor bias;

        public Linear(Tensor weight, Tensor bias) {
            if (weight.shape().rank() != 2) throw new IllegalArgumentException("linear weights must be rank two");
            this.weight = weight;
            this.bias = bias;
            if (bias != null && !java.util.Arrays.equals(bias.shape().value(), new int[]{weight.shape().value()[0]})) {
                throw new IllegalArgumentException("bias shape mismatch");
            }
        }

        public Linear(Tensor weight) {
            this(weight, null);
        }

        public List<Double> apply(List<Double> vector) {
            if (vector.size() != weight.shape().value()[1]) throw new IllegalArgumentException("linear input mismatch");
            List<Double> output = new ArrayList<>(weight.shape().value()[0]);
            for (int row = 0; row < weight.shape().value()[0]; row++) {
                double value = 0.0;
                for (int column = 0; column < weight.shape().value()[1]; column++) {
                    value += weight.data().get(row * weight.shape().value()[1] + column) * vector.get(column);
                }
                output.add(value + (bias != null ? bias.data().get(row) : 0.0));
            }
            return output;
        }

        public Tensor weight() { return weight; }
        public Tensor bias() { return bias; }
    }

    public static class RMSNorm {
        private final List<Double> weight;
        private final double epsilon;

        public RMSNorm(List<Double> weight, double epsilon) {
            this.weight = new ArrayList<>(weight);
            this.epsilon = epsilon;
        }

        public RMSNorm(List<Double> weight) {
            this(weight, 1e-6);
        }

        public List<Double> apply(List<Double> values) {
            if (values.size() != weight.size()) throw new IllegalArgumentException("norm width mismatch");
            double scale = TensorOps.rms(values, epsilon);
            List<Double> result = new ArrayList<>(values.size());
            for (int i = 0; i < values.size(); i++) {
                result.add(values.get(i) / scale * weight.get(i));
            }
            return result;
        }
    }

    public static List<Double> applyRope(List<Double> vector, int position, double base) {
        List<Double> result = new ArrayList<>(vector);
        for (int index = 0; index < vector.size() - 1; index += 2) {
            double frequency = Math.pow(base, -index / (double) vector.size());
            double angle = position * frequency;
            double x = vector.get(index);
            double y = vector.get(index + 1);
            result.set(index, x * Math.cos(angle) - y * Math.sin(angle));
            result.set(index + 1, x * Math.sin(angle) + y * Math.cos(angle));
        }
        return result;
    }

    public static class CausalSelfAttention {
        private final Linear query;
        private final Linear key;
        private final Linear value;
        private final Linear output;
        private final int heads;
        private final int headWidth;
        private final double ropeBase;

        public CausalSelfAttention(Linear query, Linear key, Linear value, Linear output, int heads, double ropeBase) {
            if (query.weight.shape().value()[0] % heads != 0) throw new IllegalArgumentException("hidden size must divide evenly among heads");
            this.query = query;
            this.key = key;
            this.value = value;
            this.output = output;
            this.heads = heads;
            this.headWidth = query.weight.shape().value()[0] / heads;
            this.ropeBase = ropeBase;
        }

        public List<List<Double>> apply(List<List<Double>> sequence) {
            if (sequence.isEmpty()) return Collections.emptyList();
            List<List<Double>> queries = new ArrayList<>(sequence.size());
            List<List<Double>> keys = new ArrayList<>(sequence.size());
            List<List<Double>> values = new ArrayList<>(sequence.size());

            for (int pos = 0; pos < sequence.size(); pos++) {
                queries.add(applyRope(query.apply(sequence.get(pos)), pos, ropeBase));
                keys.add(applyRope(key.apply(sequence.get(pos)), pos, ropeBase));
                values.add(value.apply(sequence.get(pos)));
            }

            List<List<Double>> result = new ArrayList<>(sequence.size());
            for (int pos = 0; pos < queries.size(); pos++) {
                List<Double> q = queries.get(pos);
                List<Double> merged = new ArrayList<>(heads * headWidth);
                for (int i = 0; i < heads * headWidth; i++) merged.add(0.0);

                for (int head = 0; head < heads; head++) {
                    int start = head * headWidth;
                    List<Double> scores = new ArrayList<>(pos + 1);
                    for (int keyPos = 0; keyPos <= pos; keyPos++) {
                        double score = 0.0;
                        for (int j = 0; j < headWidth; j++) {
                            score += q.get(start + j) * keys.get(keyPos).get(start + j);
                        }
                        score /= Math.sqrt(headWidth);
                        scores.add(score);
                    }
                    double maximum = scores.get(0);
                    for (double s : scores) if (s > maximum) maximum = s;
                    List<Double> probabilities = new ArrayList<>(scores.size());
                    double total = 0.0;
                    for (double score : scores) {
                        double p = Math.exp(Math.max(-80.0, score - maximum));
                        probabilities.add(p);
                        total += p;
                    }
                    if (total == 0.0) total = 1.0;
                    for (int keyPos = 0; keyPos < probabilities.size(); keyPos++) {
                        double weight = probabilities.get(keyPos) / total;
                        for (int j = 0; j < headWidth; j++) {
                            merged.set(start + j, merged.get(start + j) + weight * values.get(keyPos).get(start + j));
                        }
                    }
                }
                result.add(output.apply(merged));
            }
            return result;
        }
    }

    public static class FeedForward {
        private final Linear up;
        private final Linear down;

        public FeedForward(Linear up, Linear down) {
            this.up = up;
            this.down = down;
        }

        public List<Double> apply(List<Double> vector) {
            List<Double> hidden = up.apply(vector);
            List<Double> activated = new ArrayList<>(hidden.size());
            for (double value : hidden) {
                double clamped = Math.max(-40.0, Math.min(40.0, value));
                activated.add(value / (1.0 + Math.exp(-clamped)));
            }
            return down.apply(activated);
        }
    }

    public static class TransformerBlock {
        public final CausalSelfAttention attention;
        public final FeedForward feedForward;
        public final RMSNorm attentionNorm;
        public final RMSNorm feedForwardNorm;

        public TransformerBlock(CausalSelfAttention attention, FeedForward feedForward, RMSNorm attentionNorm, RMSNorm feedForwardNorm) {
            this.attention = attention;
            this.feedForward = feedForward;
            this.attentionNorm = attentionNorm;
            this.feedForwardNorm = feedForwardNorm;
        }

        public List<List<Double>> apply(List<List<Double>> sequence) {
            List<List<Double>> normalized = new ArrayList<>(sequence.size());
            for (List<Double> row : sequence) {
                normalized.add(attentionNorm.apply(row));
            }
            List<List<Double>> attentionOutput = attention.apply(normalized);
            List<List<Double>> residual = new ArrayList<>(sequence.size());
            for (int i = 0; i < sequence.size(); i++) {
                List<Double> row = sequence.get(i);
                List<Double> update = attentionOutput.get(i);
                List<Double> combined = new ArrayList<>(row.size());
                for (int j = 0; j < row.size(); j++) combined.add(row.get(j) + update.get(j));
                residual.add(combined);
            }
            List<List<Double>> result = new ArrayList<>(residual.size());
            for (List<Double> row : residual) {
                List<Double> ffnOut = feedForward.apply(feedForwardNorm.apply(row));
                List<Double> combined = new ArrayList<>(row.size());
                for (int j = 0; j < row.size(); j++) combined.add(row.get(j) + ffnOut.get(j));
                result.add(combined);
            }
            return result;
        }
    }

    public static class DecoderTransformer {
        private final TransformerConfig config;
        private final Tensor embeddings;
        private final List<TransformerBlock> blocks;
        private final RMSNorm finalNorm;
        private final Linear output;

        public DecoderTransformer(TransformerConfig config, Tensor embeddings, List<TransformerBlock> blocks, RMSNorm finalNorm, Linear output) {
            if (!java.util.Arrays.equals(embeddings.shape().value(), new int[]{config.vocabularySize(), config.hiddenSize()})) {
                throw new IllegalArgumentException("embedding shape mismatch");
            }
            this.config = config;
            this.embeddings = embeddings;
            this.blocks = new ArrayList<>(blocks);
            this.finalNorm = finalNorm;
            this.output = output;
        }

        public List<List<Double>> forward(List<Integer> tokenIds) {
            if (tokenIds.size() > config.contextLength()) {
                tokenIds = tokenIds.subList(tokenIds.size() - config.contextLength(), tokenIds.size());
            }
            List<List<Double>> sequence = new ArrayList<>(tokenIds.size());
            for (int token : tokenIds) {
                sequence.add(embeddings.row(token));
            }
            for (TransformerBlock block : blocks) {
                sequence = block.apply(sequence);
            }
            List<List<Double>> result = new ArrayList<>(sequence.size());
            for (List<Double> row : sequence) {
                result.add(output.apply(finalNorm.apply(row)));
            }
            return result;
        }

        public List<Double> logits(List<Integer> tokenIds) {
            if (tokenIds.isEmpty()) throw new IllegalArgumentException("at least one token required");
            return forward(tokenIds).get(tokenIds.size() - 1);
        }

        public TransformerConfig config() { return config; }
        public Tensor embeddings() { return embeddings; }
        public List<TransformerBlock> blocks() { return Collections.unmodifiableList(blocks); }
        public RMSNorm finalNorm() { return finalNorm; }
        public Linear output() { return output; }
    }
}
