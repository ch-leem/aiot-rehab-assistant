package com.example.iot.redis.dto;

public record LatestResponse(
        boolean ok,
        String key,
        JointLatestValue data
) {}