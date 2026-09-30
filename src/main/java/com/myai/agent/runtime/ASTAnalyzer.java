package com.myai.agent.runtime;

public class ASTAnalyzer {
    public ASTAnalyzer() {}

    public void parse(String source, String filename) {
        throw new UnsupportedOperationException("AST analysis is Java-native");
    }

    public java.util.List<java.util.Map<String, Object>> symbols(String source) {
        throw new UnsupportedOperationException("AST analysis is Java-native");
    }

    public java.util.List<String> imports(String source) {
        throw new UnsupportedOperationException("AST analysis is Java-native");
    }

    public java.util.List<String> validateFile(String path) {
        throw new UnsupportedOperationException("AST analysis is Java-native");
    }
}
