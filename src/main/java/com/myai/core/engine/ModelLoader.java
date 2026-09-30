package com.myai.core.engine;

import java.io.IOException;
import java.nio.file.Path;
import java.util.*;
import java.util.function.Function;

public class ModelLoader {
    public static Function<List<Map<String, String>>, String> loadLocalModel(Map<String, Object> config) {
        Map<String, Object> modelCfg = (Map<String, Object>) config.getOrDefault("model", Map.of());
        String pathStr = (String) modelCfg.getOrDefault("path", "");
        if (pathStr.isEmpty()) return null;

        Path path = Path.of(pathStr);
        if (!path.toFile().isFile()) return null;

        Tokenizer tokenizer;
        String tokenizerPath = (String) modelCfg.getOrDefault("tokenizer", "");
        if (!tokenizerPath.isEmpty()) {
            try {
                tokenizer = Tokenizer.fromJson(tokenizerPath);
            } catch (IOException e) {
                tokenizer = new Tokenizer(null, List.of());
            }
        } else {
            Path candidate = path.resolveSibling("tokenizer.json");
            if (candidate.toFile().isFile()) {
                try {
                    tokenizer = Tokenizer.fromJson(candidate.toString());
                } catch (IOException e) {
                    tokenizer = new Tokenizer(null, List.of());
                }
            } else {
                tokenizer = new Tokenizer(null, List.of());
            }
        }

        Map<String, Object> runtime = (Map<String, Object>) config.getOrDefault("runtime", Map.of());

        Map<String, Tensor> records;
        try (WeightsParser.WeightFile wf = new WeightsParser.WeightFile(path)) {
            records = new LinkedHashMap<>();
            for (String name : wf.names()) {
                records.put(name, wf.read(name));
            }
        } catch (IOException e) {
            return null;
        }

        int vocabSize = tokenizer.vocabularySize();
        int ctx = (Integer) modelCfg.getOrDefault("context_length", 2048);
        int hidden = (Integer) modelCfg.getOrDefault("hidden_size", 256);
        int layers = (Integer) modelCfg.getOrDefault("layers", 4);
        int heads = (Integer) modelCfg.getOrDefault("heads", 4);
        int intermediate = (Integer) modelCfg.getOrDefault("intermediate_size", hidden * 4);

        Transformer.TransformerConfig transformerConfig = new Transformer.TransformerConfig(vocabSize, ctx, hidden, layers, heads, intermediate);

        Tensor embeddings = first(records, "tok_embeddings", "embeddings", "word_embeddings");
        if (embeddings == null) throw new IllegalArgumentException("missing embeddings weight");

        Tensor finalNormData = first(records, "final_norm", "ln_f", "layer_norm");
        if (finalNormData == null) throw new IllegalArgumentException("missing final norm weight");
        Transformer.RMSNorm finalNorm = new Transformer.RMSNorm(finalNormData.data());

        Tensor outputWeight = first(records, "lm_head", "output", "word_embeddings");
        if (outputWeight == null) outputWeight = embeddings;
        Transformer.Linear output = new Transformer.Linear(outputWeight);

        List<Transformer.TransformerBlock> blocks = new ArrayList<>();
        for (int i = 0; i < layers; i++) {
            String p = "layers." + i;

            Tensor q = first(records, p + ".attention.query_proj", p + ".query", p + ".attn.q_proj");
            Tensor k = first(records, p + ".attention.key_proj", p + ".key", p + ".attn.k_proj");
            Tensor v = first(records, p + ".attention.value_proj", p + ".value", p + ".attn.v_proj");
            Tensor o = first(records, p + ".attention.output_proj", p + ".output", p + ".attn.o_proj");
            if (q == null || k == null || v == null || o == null) throw new IllegalArgumentException("missing attention weights for layer " + i);

            Transformer.CausalSelfAttention attention = new Transformer.CausalSelfAttention(
                new Transformer.Linear(q), new Transformer.Linear(k), new Transformer.Linear(v), new Transformer.Linear(o),
                heads, transformerConfig.ropeBase()
            );

            Tensor up = first(records, p + ".feed_forward.w1", p + ".up_proj", p + ".mlp.gate_proj");
            Tensor down = first(records, p + ".feed_forward.w2", p + ".down_proj", p + ".mlp.down_proj");
            if (up == null || down == null) throw new IllegalArgumentException("missing feed forward weights for layer " + i);
            Transformer.FeedForward feedForward = new Transformer.FeedForward(new Transformer.Linear(up), new Transformer.Linear(down));

            Tensor attnNorm = first(records, p + ".attention_norm", p + ".ln1", p + ".ln_attn");
            Tensor ffnNorm = first(records, p + ".feed_forward_norm", p + ".ln2", p + ".ln_mlp");
            if (attnNorm == null || ffnNorm == null) throw new IllegalArgumentException("missing norm weights for layer " + i);

            blocks.add(new Transformer.TransformerBlock(
                attention, feedForward,
                new Transformer.RMSNorm(attnNorm.data()),
                new Transformer.RMSNorm(ffnNorm.data())
            ));
        }

        Transformer.DecoderTransformer transformer = new Transformer.DecoderTransformer(transformerConfig, embeddings, blocks, finalNorm, output);
        Sampler.SamplingConfig samplingConfig = new Sampler.SamplingConfig(
            (Double) runtime.getOrDefault("temperature", 0.7),
            (Integer) runtime.getOrDefault("top_k", 40),
            (Double) runtime.getOrDefault("top_p", 0.9)
        );
        Sampler sampler = new Sampler(samplingConfig);

        int eosToken = tokenizer.getVocabulary().getOrDefault("<eos>", -1);

        return messages -> {
            StringBuilder prompt = new StringBuilder();
            for (Map<String, String> m : messages) {
                prompt.append(m.getOrDefault("role", "user")).append(": ").append(m.getOrDefault("content", "")).append("\n");
            }
            List<Integer> tokenIds = tokenizer.encode(prompt.toString());
            int maxNew = (Integer) runtime.getOrDefault("max_new_tokens", 32);
            List<Integer> generated = new ArrayList<>(tokenIds);

            for (int i = 0; i < maxNew; i++) {
                if (generated.size() > ctx) {
                    generated = new ArrayList<>(generated.subList(generated.size() - ctx, generated.size()));
                }
                List<Double> logits = transformer.logits(generated);
                List<Integer> history = new ArrayList<>(generated);
                int nextId = sampler.sample(logits, history);
                generated.add(nextId);
                if (eosToken >= 0 && nextId == eosToken) break;
            }

            List<Integer> newIds = generated.subList(tokenIds.size(), generated.size());
            String text = tokenizer.decode(newIds);
            if (!isReadable(text)) return null;
            return text;
        };
    }

    private static boolean isReadable(String text) {
        if (text == null || text.isEmpty()) return false;
        text = text.strip();
        if (text.isEmpty()) return false;
        int printable = 0;
        for (char ch : text.toCharArray()) {
            if (Character.isPrintable(ch) || Character.isWhitespace(ch)) printable++;
        }
        return printable >= (int) Math.max(1, text.length() * 0.7);
    }

    private static Tensor first(Map<String, Tensor> records, String... names) {
        for (String name : names) {
            if (records.containsKey(name)) return records.get(name);
        }
        return null;
    }
}
