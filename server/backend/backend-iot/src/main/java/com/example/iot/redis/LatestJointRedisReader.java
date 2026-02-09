package com.example.iot.redis;

import com.example.iot.redis.dto.JointLatestValue;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.util.Optional;
@Slf4j
@Component
public class LatestJointRedisReader {

    private final StringRedisTemplate redis;
    private final ObjectMapper objectMapper;

    public LatestJointRedisReader(StringRedisTemplate redis, ObjectMapper objectMapper) {
        this.redis = redis;
        this.objectMapper = objectMapper;
    }

    public Optional<JointLatestValue> getLatest(String deviceId, String joint) {
        String key = RedisKeys.latestKey(deviceId, joint);
        String raw = redis.opsForValue().get(key);
        if (raw == null) return Optional.empty();

        log.info("[REDIS] RAW key={} value={}", key, raw);

        try {
            JointLatestValue value =
                    objectMapper.readValue(raw, JointLatestValue.class);

            log.info(
                    "[REDIS] PARSED device={} joint={} x={} y={} z={} ts={}",
                    deviceId, joint,
                    value.x(), value.y(), value.z(), value.ts()
            );

            return Optional.of(value);
        } catch (Exception e) {
            throw new IllegalStateException("Bad redis json: key=" + key + ", raw=" + raw, e);
        }
    }
}