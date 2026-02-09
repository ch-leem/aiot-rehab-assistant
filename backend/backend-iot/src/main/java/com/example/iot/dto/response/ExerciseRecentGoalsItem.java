package com.example.iot.dto.response;

import java.util.List;

public record ExerciseRecentGoalsItem(
        Long exerciseId,
        String exerciseName,
        List<String> goals   // 최근 5개(오늘 제외)
) {}
