package com.myai.core.engine;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.MappedByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.*;

public class Tensor {
    public record Shape(int[] value) {
        public Shape { value = value != null ? value.clone() : new int[0]; }
        public int rank() { return value.length; }
        public int size() { int s = 1; for (int d : value) s *= d; return s; }
    }

    private final Shape shape;
    private final List<Double> data;

    public Tensor(Shape shape, List<Double> data) {
        if (shape == null || shape.value().length == 0) {
            throw new IllegalArgumentException("shape must contain non-negative dimensions");
        }
        int expected = shape.size();
        if (data.size() != expected) {
            throw new IllegalArgumentException("shape " + java.util.Arrays.toString(shape.value()) + " requires " + expected + " values, got " + data.size());
        }
        this.shape = shape;
        this.data = new ArrayList<>(data);
    }

    public Tensor(int[] shape, double[] values) {
        this(new Shape(shape), listFromArray(values));
    }

    private static List<Double> listFromArray(double[] arr) {
        List<Double> list = new ArrayList<>(arr.length);
        for (double v : arr) list.add(v);
        return list;
    }

    public Shape shape() { return shape; }
    public List<Double> data() { return Collections.unmodifiableList(data); }
    List<Double> mutableData() { return data; }
    public int size() { return data.size(); }

    public static Tensor zeros(int[] shape) {
        int size = 1;
        for (int d : shape) size *= d;
        return new Tensor(shape, new double[size]);
    }

    public static Tensor filled(int[] shape, double value) {
        int size = 1;
        for (int d : shape) size *= d;
        double[] values = new double[size];
        java.util.Arrays.fill(values, value);
        return new Tensor(shape, values);
    }

    public static Tensor fromNested(List<?> values) {
        List<Double> flat = new ArrayList<>();
        List<Integer> dims = new ArrayList<>();
        flatten(values, dims, flat, 0);
        int[] shapeArr = dims.stream().mapToInt(Integer::intValue).toArray();
        return new Tensor(new Shape(shapeArr), flat);
    }

    private static void flatten(Object value, List<Integer> dims, List<Double> flat, int depth) {
        if (value instanceof List<?> list) {
            if (dims.size() <= depth) dims.add(list.size());
            else if (dims.get(depth) != list.size()) throw new IllegalArgumentException("ragged nested data");
            for (Object item : list) flatten(item, dims, flat, depth + 1);
        } else {
            flat.add(((Number) value).doubleValue());
        }
    }

    public Tensor clone() {
        return new Tensor(shape, new ArrayList<>(data));
    }

    public double get(int... indices) {
        if (indices.length != shape.rank()) throw new IndexOutOfBoundsException("wrong rank");
        int offset = 0;
        for (int i = 0; i < indices.length; i++) {
            if (indices[i] < 0 || indices[i] >= shape.value()[i]) throw new IndexOutOfBoundsException("index out of bounds");
            offset = offset * shape.value()[i] + indices[i];
        }
        return data.get(offset);
    }

    public void set(int[] indices, double value) {
        if (indices.length != shape.rank()) throw new IndexOutOfBoundsException("wrong rank");
        int offset = 0;
        for (int i = 0; i < indices.length; i++) {
            if (indices[i] < 0 || indices[i] >= shape.value()[i]) throw new IndexOutOfBoundsException("index out of bounds");
            offset = offset * shape.value()[i] + indices[i];
        }
        data.set(offset, value);
    }

    public List<Double> row(int index) {
        if (shape.rank() != 2) throw new IllegalArgumentException("row requires a matrix");
        int start = index * shape.value()[1];
        int end = start + shape.value()[1];
        return new ArrayList<>(data.subList(start, end));
    }

    public Tensor map(java.util.function.Function<Double, Double> function) {
        List<Double> mapped = new ArrayList<>(data.size());
        for (double x : data) mapped.add(function.apply(x));
        return new Tensor(shape, mapped);
    }

    public Tensor add(Tensor other) {
        if (!java.util.Arrays.equals(this.shape.value(), other.shape.value())) throw new IllegalArgumentException("shape mismatch");
        List<Double> result = new ArrayList<>(this.data.size());
        for (int i = 0; i < this.data.size(); i++) {
            result.add(this.data.get(i) + other.data.get(i));
        }
        return new Tensor(this.shape, result);
    }

    public Tensor scale(double factor) {
        List<Double> result = new ArrayList<>(data.size());
        for (double x : data) result.add(x * factor);
        return new Tensor(shape, result);
    }

    public Tensor reshape(int[] newShape) {
        return new Tensor(new Shape(newShape), new ArrayList<>(data));
    }

    public Tensor transpose() {
        if (shape.rank() != 2) throw new IllegalArgumentException("transpose currently supports matrices");
        int rows = shape.value()[0];
        int cols = shape.value()[1];
        List<Double> result = new ArrayList<>(data.size());
        for (int col = 0; col < cols; col++) {
            for (int row = 0; row < rows; row++) {
                result.add(data.get(row * cols + col));
            }
        }
        return new Tensor(new Shape(new int[]{cols, rows}), result);
    }

    public Tensor matmul(Tensor other) {
        if (this.shape.rank() != 2 || other.shape.rank() != 2 || this.shape.value()[1] != other.shape.value()[0]) {
            throw new IllegalArgumentException("matrix shape mismatch");
        }
        int rows = this.shape.value()[0];
        int inner = this.shape.value()[1];
        int cols = other.shape.value()[1];
        List<Double> result = new ArrayList<>(rows * cols);
        for (int i = 0; i < rows * cols; i++) result.add(0.0);
        for (int row = 0; row < rows; row++) {
            for (int pivot = 0; pivot < inner; pivot++) {
                double coefficient = data.get(row * inner + pivot);
                for (int col = 0; col < cols; col++) {
                    result.set(row * cols + col, result.get(row * cols + col) + coefficient * other.data.get(pivot * cols + col));
                }
            }
        }
        return new Tensor(new Shape(new int[]{rows, cols}), result);
    }

    public Tensor softmax(int axis) {
        if (axis != -1 && axis != shape.rank() - 1) throw new IllegalArgumentException("only final-axis softmax is supported");
        int width = shape.value()[shape.rank() - 1];
        List<Double> result = new ArrayList<>(data.size());
        for (int start = 0; start < data.size(); start += width) {
            List<Double> row = data.subList(start, start + width);
            double maximum = row.get(0);
            for (double v : row) if (v > maximum) maximum = v;
            List<Double> values = new ArrayList<>(row.size());
            double total = 0.0;
            for (double x : row) {
                double v = Math.exp(Math.max(-80.0, Math.min(80.0, x - maximum)));
                values.add(v);
                total += v;
            }
            if (total == 0.0) total = 1.0;
            for (double v : values) result.add(v / total);
        }
        return new Tensor(shape, result);
    }

    public Tensor l2NormalizeRows(double epsilon) {
        if (shape.rank() != 2) throw new IllegalArgumentException("row normalization requires a matrix");
        int width = shape.value()[1];
        List<Double> output = new ArrayList<>(data.size());
        for (int start = 0; start < data.size(); start += width) {
            double norm = 0.0;
            for (int i = start; i < start + width; i++) norm += data.get(i) * data.get(i);
            norm = Math.sqrt(norm + epsilon);
            for (int i = start; i < start + width; i++) output.add(data.get(i) / norm);
        }
        return new Tensor(shape, output);
    }

    public static class MappedFloat32 implements AutoCloseable {
        private final java.nio.file.Path path;
        private final long offset;
        private final int count;
        private final java.nio.channels.FileChannel channel;
        private final MappedByteBuffer mapping;
        private final java.nio.FloatBuffer buffer;

        public MappedFloat32(Path path, long offset, int count) throws IOException {
            this.path = path;
            this.offset = offset;
            this.count = count;
            this.channel = java.nio.channels.FileChannel.open(path, StandardOpenOption.READ);
            this.mapping = channel.map(java.nio.channels.FileChannel.MapMode.READ_ONLY, offset, count * 4L);
            this.buffer = mapping.asFloatBuffer();
        }

        public int length() { return count; }
        public float get(int index) {
            if (index < 0 || index >= count) throw new IndexOutOfBoundsException(String.valueOf(index));
            return buffer.get(index);
        }
        public Iterator<Float> iterator() {
            return new Iterator<Float>() {
                private int pos = 0;
                public boolean hasNext() { return pos < count; }
                public Float next() { return get(pos++); }
            };
        }
        public void close() throws IOException {
            java.nio.channels.FileChannel channel = this.channel;
            if (channel != null && channel.isOpen()) channel.close();
        }
    }
}
