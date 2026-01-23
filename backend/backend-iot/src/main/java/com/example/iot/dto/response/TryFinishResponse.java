package com.example.iot.dto.response;

public record TryFinishResponse (
        Long tryId,
        String text
//        String failType,
//        String goalSensor,
//        String goalVision
) {}