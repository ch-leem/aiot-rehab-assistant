package com.example.iot.redis.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public record JointLatestValue(
        double x,
        double y,
        double z,
        String ts
) {}