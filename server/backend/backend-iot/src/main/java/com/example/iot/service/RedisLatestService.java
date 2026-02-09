package com.example.iot.service;


import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class RedisLatestService {
    private final StringRedisTemplate redis;

    // 저장
    public void saveLatest(String key, String json) {
        redis.opsForValue().set(key, json);
    }

    // 조회
    public String getLatest(String key) {
        return redis.opsForValue().get(key);
    }
}
