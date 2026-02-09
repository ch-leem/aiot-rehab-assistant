package com.example.iot.dto.response;

public record SequenceAverageResponse(
        Long sequenceId,
        double averageRate
) {}
