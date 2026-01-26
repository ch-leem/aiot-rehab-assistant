package com.example.iot.dto.response;

import java.math.BigDecimal;

public class SessionTryCountResponse {
    private Long sessionId;
    private int totalTries;
    private int successTries;

    public SessionTryCountResponse(Long sessionId, int totalTries, int successTries) {
        this.sessionId = sessionId;
        this.totalTries = totalTries;
        this.successTries = successTries;
    }

    public Long getSessionId() { return sessionId; }
    public int getTotalTries() { return totalTries; }
    public int getSuccessTries() { return successTries; }
}