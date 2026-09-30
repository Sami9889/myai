package com.myai.core.engine;

import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.channels.FileChannel;
import java.nio.file.Path;
import java.util.*;

public class WeightsParser {
    private static final byte[] MAGIC = new byte[]{'M', 'Y', 'A', 'I', 'W', '0', '1', 0};

    public record WeightRecord(String name, int[] shape, long offset, int count) {
    }

    public static class WeightFile implements AutoCloseable {
        private final Path path;
        private final RandomAccessFile file;
        private final FileChannel channel;
        private final Map<String, WeightRecord> records;

        public WeightFile(Path path) throws IOException {
            this.path = path;
            this.file = new RandomAccessFile(path.toFile(), "r");
            this.channel = file.getChannel();
            this.records = new LinkedHashMap<>();
            parse();
        }

        private void parse() throws IOException {
            ByteBuffer buffer = ByteBuffer.allocate(8).order(ByteOrder.LITTLE_ENDIAN);
            channel.read(buffer);
            buffer.flip();
            byte[] magic = new byte[8];
            buffer.get(magic);
            if (!java.util.Arrays.equals(magic, MAGIC)) throw new IllegalArgumentException("invalid MYAI weight magic");

            buffer = ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN);
            channel.read(buffer);
            buffer.flip();
            int count = buffer.getInt();

            for (int i = 0; i < count; i++) {
                buffer = ByteBuffer.allocate(2).order(ByteOrder.LITTLE_ENDIAN);
                channel.read(buffer);
                buffer.flip();
                int nameLength = buffer.getShort() & 0xFFFF;

                byte[] nameBytes = new byte[nameLength];
                channel.read(ByteBuffer.wrap(nameBytes));
                String name = new String(nameBytes, java.nio.charset.StandardCharsets.UTF_8);

                buffer = ByteBuffer.allocate(1).order(ByteOrder.LITTLE_ENDIAN);
                channel.read(buffer);
                buffer.flip();
                int rank = buffer.get() & 0xFF;

                int[] shape = new int[rank];
                for (int r = 0; r < rank; r++) {
                    buffer = ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN);
                    channel.read(buffer);
                    buffer.flip();
                    shape[r] = buffer.getInt();
                }

                int size = 1;
                for (int d : shape) size *= d;
                long offset = channel.position();
                channel.position(channel.position() + size * 4L);

                records.put(name, new WeightRecord(name, shape, offset, size));
            }
        }

        public Set<String> names() { return Collections.unmodifiableSet(records.keySet()); }

        public Tensor read(String name) throws IOException {
            WeightRecord record = records.get(name);
            if (record == null) throw new IllegalArgumentException("weight not found: " + name);
            ByteBuffer buffer = ByteBuffer.allocate(record.count() * 4).order(ByteOrder.LITTLE_ENDIAN);
            channel.read(buffer, record.offset());
            buffer.flip();
            double[] data = new double[record.count()];
            for (int i = 0; i < record.count(); i++) {
                data[i] = buffer.getFloat();
            }
            return new Tensor(new Tensor.Shape(record.shape()), data);
        }

        public void close() throws IOException {
            channel.close();
            file.close();
        }
    }

    public static void writeWeights(Path path, Map<String, Tensor> tensors) throws IOException {
        try (var stream = new java.io.FileOutputStream(path.toFile())) {
            stream.write(MAGIC);
            stream.write(new byte[]{(byte) (tensors.size() & 0xFF), (byte) ((tensors.size() >> 8) & 0xFF), (byte) ((tensors.size() >> 16) & 0xFF), (byte) ((tensors.size() >> 24) & 0xFF)});
            for (Map.Entry<String, Tensor> entry : tensors.entrySet()) {
                byte[] nameBytes = entry.getKey().getBytes(java.nio.charset.StandardCharsets.UTF_8);
                stream.write(new byte[]{(byte) (nameBytes.length & 0xFF), (byte) ((nameBytes.length >> 8) & 0xFF)});
                stream.write(nameBytes);
                int rank = entry.getValue().shape().rank();
                stream.write(rank);
                for (int d : entry.getValue().shape().value()) {
                    byte[] bytes = ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putInt(d).array();
                    stream.write(bytes);
                }
                List<Double> data = entry.getValue().data();
                for (double v : data) {
                    byte[] bytes = ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putFloat((float) v).array();
                    stream.write(bytes);
                }
            }
        }
    }
}
