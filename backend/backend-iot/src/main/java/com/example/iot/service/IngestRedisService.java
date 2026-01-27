package com.example.iot.service;

import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.Map;

@Service
public class IngestRedisService {

    private final StringRedisTemplate redisTemplate;

    public IngestRedisService(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    public String getLatest() {
        return redisTemplate.opsForValue().get("ingest:latest");
    }

    public Map<Object, Object> getAgg(Long tryId) {
        String key = "agg:try:" + tryId;
        return redisTemplate.opsForHash().entries(key);
    }
}