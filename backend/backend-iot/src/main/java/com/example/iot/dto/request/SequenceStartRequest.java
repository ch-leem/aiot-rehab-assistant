package com.example.iot.dto.request;

public record SequenceStartRequest(
        Integer tryCount // null이면 기본값 사용(10)
) {}