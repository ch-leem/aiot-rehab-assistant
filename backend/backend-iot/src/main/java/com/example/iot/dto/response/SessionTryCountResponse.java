package com.example.iot.dto.response;

import java.math.BigDecimal;

public class SessionTryCountResponse {
    private Long exerciseId;
    private int totalTries;
    private int successTries;

    public SessionTryCountResponse(Long exerciseId, int totalTries, int successTries) {
        this.exerciseId = exerciseId;
        this.totalTries = totalTries;
        this.successTries = successTries;
    }

    public Long getExerciseId() { return exerciseId; }
    public int getTotalTries() { return totalTries; }
    public int getSuccessTries() { return successTries; }
}