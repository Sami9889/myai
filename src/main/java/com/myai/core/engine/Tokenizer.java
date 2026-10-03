package com.myai.core.engine;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class Tokenizer {

    private record MergePair(String first, String second) {
    }

    private final Map<String, Integer> vocabulary;
    private final Map<Integer, byte[]> inverse;
    private final Map<MergePair, Integer> ranks;
    private final int unknownId;

    public Tokenizer(Map<String, Integer> vocabulary, List<MergePair> merges) {
        if (vocabulary == null) {
            this.vocabulary = new HashMap<>();
            for (int i = 0; i < 256; i++) {
                this.vocabulary.put(new String(new byte[]{(byte) i}, StandardCharsets.ISO_8859_1), i);
            }
        } else {
            this.vocabulary = vocabulary;
        }
        this.inverse = new HashMap<>();
        for (Map.Entry<String, Integer> entry : this.vocabulary.entrySet()) {
            inverse.put(entry.getValue(), entry.getKey().getBytes(StandardCharsets.UTF_8));
        }
        this.ranks = new HashMap<>();
        int rank = 0;
        for (MergePair pair : merges) {
            ranks.put(pair, rank++);
        }
        this.unknownId = this.vocabulary.getOrDefault("<unk>", 0);
    }

    public static Tokenizer fromJson(String path) throws IOException {
        String content = Files.readString(Path.of(path));
        Map<String, Integer> vocab = new LinkedHashMap<>();
        List<MergePair> merges = new ArrayList<>();

        int vocabStart = content.indexOf("\"vocab\"");
        if (vocabStart >= 0) {
            int objStart = content.indexOf("{", vocabStart);
            int objEnd = findMatchingBrace(content, objStart);
            String vocabSection = content.substring(objStart, objEnd + 1);
            Pattern pattern = Pattern.compile("\"([^\"]+)\"\\s*:\\s*(\\d+)");
            Matcher matcher = pattern.matcher(vocabSection);
            while (matcher.find()) {
                vocab.put(matcher.group(1), Integer.parseInt(matcher.group(2)));
            }
        }

        int mergesStart = content.indexOf("\"merges\"");
        if (mergesStart >= 0) {
            int arrStart = content.indexOf("[", mergesStart);
            int arrEnd = findMatchingBracket(content, arrStart);
            String mergesSection = content.substring(arrStart + 1, arrEnd);
            Pattern pattern = Pattern.compile("\"([^\"]+)\\s+([^\"]+)\"");
            Matcher matcher = pattern.matcher(mergesSection);
            while (matcher.find()) {
                merges.add(new MergePair(matcher.group(1), matcher.group(2)));
            }
        }

        return new Tokenizer(vocab, merges);
    }

    private static int findMatchingBrace(String s, int start) {
        int depth = 0;
        for (int i = start; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '{') depth++;
            else if (c == '}') {
                depth--;
                if (depth == 0) return i;
            }
        }
        return s.length() - 1;
    }

    private static int findMatchingBracket(String s, int start) {
        int depth = 0;
        for (int i = start; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '[') depth++;
            else if (c == ']') {
                depth--;
                if (depth == 0) return i;
            }
        }
        return s.length() - 1;
    }

    private List<String> initial(byte[] data) {
        List<String> result = new ArrayList<>(data.length);
        for (byte b : data) {
            result.add(new String(new byte[]{b}, StandardCharsets.ISO_8859_1));
        }
        return result;
    }

    private List<String> mergeOnce(List<String> symbols) {
        Integer bestRank = null;
        int bestIndex = -1;
        MergePair bestPair = null;
        for (int i = 0; i < symbols.size() - 1; i++) {
            MergePair pair = new MergePair(symbols.get(i), symbols.get(i + 1));
            Integer rank = ranks.get(pair);
            if (rank != null && (bestRank == null || rank < bestRank)) {
                bestRank = rank;
                bestIndex = i;
                bestPair = pair;
            }
        }
        if (bestPair == null) return symbols;
        List<String> result = new ArrayList<>(symbols.size() - 1);
        result.addAll(symbols.subList(0, bestIndex));
        result.add(bestPair.first() + bestPair.second());
        result.addAll(symbols.subList(bestIndex + 2, symbols.size()));
        return result;
    }

    public List<Integer> encodeBytes(byte[] data) {
        List<String> symbols = initial(data);
        while (true) {
            List<String> merged = mergeOnce(symbols);
            if (merged == symbols) break;
            symbols = merged;
        }
        List<Integer> result = new ArrayList<>(symbols.size());
        for (String symbol : symbols) {
            result.add(vocabulary.getOrDefault(symbol, unknownId));
        }
        return result;
    }

    public List<Integer> encode(String text) {
        return encodeBytes(text.getBytes(StandardCharsets.UTF_8));
    }

    public String decode(Iterable<Integer> ids) {
        List<Byte> allBytes = new ArrayList<>();
        for (int id : ids) {
            byte[] bytes = inverse.getOrDefault(id, "<unk>".getBytes(StandardCharsets.UTF_8));
            for (byte b : bytes) allBytes.add(b);
        }
        byte[] arr = new byte[allBytes.size()];
        for (int i = 0; i < allBytes.size(); i++) arr[i] = allBytes.get(i);
        return new String(arr, StandardCharsets.UTF_8);
    }

    public byte[] tokenText(int tokenId) {
        return inverse.getOrDefault(tokenId, "<unk>".getBytes(StandardCharsets.UTF_8));
    }

    public int vocabularySize() {
        return vocabulary.values().stream().mapToInt(Integer::intValue).max().orElse(-1) + 1;
    }

    public Map<String, Integer> getVocabulary() {
        return Collections.unmodifiableMap(vocabulary);
    }
}
