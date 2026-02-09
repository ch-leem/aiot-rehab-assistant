package com.example.iot.service;

import com.example.iot.redis.RedisKeys;
import com.example.iot.redis.dto.JointLatestValue;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.Optional;

@Service
public class LatestPoseService {

    private final StringRedisTemplate redis;
    private final ObjectMapper objectMapper;

    public LatestPoseService(StringRedisTemplate redis, ObjectMapper objectMapper) {
        this.redis = redis;
        this.objectMapper = objectMapper;
    }

    public Optional<JointLatestValue> getLatest(String deviceId, String joint) {
        String key = RedisKeys.latestKey(deviceId, joint);
        String raw = redis.opsForValue().get(key);
        if (raw == null) return Optional.empty();

        try {
            JointLatestValue value = objectMapper.readValue(raw, JointLatestValue.class);
            return Optional.of(value);
        } catch (Exception e) {
            // JSON이 깨졌거나 예상과 다르면 Optional.empty() 대신 예외 던져도 됨
            throw new IllegalStateException("Failed to parse redis value for key=" + key + " raw=" + raw, e);
        }
    }

    public String buildKey(String deviceId, String joint) {
        return RedisKeys.latestKey(deviceId, joint);
    }
}