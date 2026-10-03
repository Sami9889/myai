package com.myai.core.engine;

public record Token(int id, byte[] text) {
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Token token)) return false;
        return id == token.id && java.util.Arrays.equals(text, token.text);
    }

    @Override
    public int hashCode() {
        int result = Integer.hashCode(id);
        result = 31 * result + java.util.Arrays.hashCode(text);
        return result;
    }
}
