package com.example.iot.service;

import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

@Service
public class IngestRedisService {

    private final StringRedisTemplate redisTemplate;

    public IngestRedisService(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    public String getLatest() {
        return redisTemplate.opsForValue().get("ingest:latest");
    }
}