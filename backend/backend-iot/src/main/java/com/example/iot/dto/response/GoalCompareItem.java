package com.example.iot.dto.response;

public record GoalCompareItem(
        Long exerciseId,
        String exerciseName,
        String previousGoal,
        String currentGoal,
        String diff
) {}
