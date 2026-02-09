package com.example.iot.dto.response;


import java.util.List;

public record SequenceCompareResponse(
        Long patientId,
        Long currentSequenceId,
        Long previousSequenceId,
        List<GoalCompareItem> items
) {}