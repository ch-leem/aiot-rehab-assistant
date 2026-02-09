package com.example.user.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;

import java.util.List;

@Getter
@Builder
@AllArgsConstructor
public class SequenceDetailResponse {
    private Long sequenceId;
    private String feedback;
    private List<SummaryInfo> summaries; // 단일 객체에서 List로 변경
    private List<SessionItem> sessions;

    @Getter
    @Builder
    public static class SummaryInfo {
        private Long exerciseId;       // 추가
        private Double successRate;    // 명칭 변경 (inTargetRate -> successRate)
        private Double averageScore;   // 명칭 변경 (avgAngle -> averageScore)
        private String summaryTag;     // 명칭 변경 (stabilityLevel -> summaryTag)
        private String sessionNote;    // 추가
    }

    @Getter
    @Builder
    public static class SessionItem {
        private Long sessionId;
        private String exerciseName;
        private String goal;
        private int totalTries;        // 추가
        private int successTries;      // 추가
    }
}