package com.myai.utils;

public class ValidationError extends IllegalArgumentException {
    public ValidationError(String message) { super(message); }
}
