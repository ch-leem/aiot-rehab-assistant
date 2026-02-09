package com.example.user.dto;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class PatientReportResponse {
    private Long patientId;
    private String patientName;

    // 세션 요약(SessionSummary) 관련 정보
    private Long totalTrials;
    private Long successTrials;

    private Double averageScore;
    private Double successRate;
    private String summaryTag;
}