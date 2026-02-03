package com.example.iot.service;

import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Stream;

@Service
@RequiredArgsConstructor
public class TryRawDumpService {
    private final StringRedisTemplate redis;
    //test주석
    // 저장 폴더 (도커면 볼륨 마운트 추천)
    private static final Path BASE_DIR = Paths.get("/data/fail-logs");

    public Path dumpRawAsJsonl(Long tryId, boolean deleteAfter) throws IOException {
        String key = "try:" + tryId + ":raw";

        // 1) LRANGE로 전체 가져오기
        List<String> rows = redis.opsForList().range(key, 0, -1);

        if (rows == null || rows.isEmpty()) {
            throw new IllegalStateException("raw list is empty or missing. key=" + key);
        }

        // 2) 파일 경로 준비
        Files.createDirectories(BASE_DIR);

        String ts = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss"));
        Path file = BASE_DIR.resolve("try-" + tryId + "-" + ts + ".jsonl");

        // 3) 줄 단위로 저장 (각 줄이 JSON)
        try (BufferedWriter w = Files.newBufferedWriter(file, StandardCharsets.UTF_8,
                StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)) {

            for (String line : rows) {
                w.write(line);
                w.newLine();
            }
        }

        // 4) 원하면 Redis raw 삭제
        if (deleteAfter) {
            redis.delete(key);
        }

        return file;
    }

    public Path findLatestDumpFile(Long tryId) throws Exception {
        if (!Files.exists(BASE_DIR)) {
            throw new IllegalStateException("fail-logs dir not found: " + BASE_DIR);
        }
        String prefix = "try-" + tryId + "-";

        try (Stream<Path> s = Files.list(BASE_DIR)) {
            return s.filter(p -> p.getFileName().toString().startsWith(prefix))
                    .filter(p -> p.getFileName().toString().endsWith(".jsonl"))
                    .max(Comparator.comparingLong(p -> p.toFile().lastModified()))
                    .orElseThrow(() ->
                            new IllegalStateException("fail log file not found for tryId=" + tryId));
        }
    }
}
