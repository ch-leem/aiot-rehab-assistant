package com.example.user.dto;

import com.example.iot.domain.Sequence;
import com.example.iot.domain.SessionSummary;
import lombok.Builder;
import lombok.Getter;

import java.util.List;

@Getter
@Builder
public class SequenceDetailResponse {
    private Long sequenceId;
    private String feedback;

    // SessionSummary 정보 (1:1 관계)
    private SummaryInfo summary;

    // 하위 세션 리스트
    private List<SessionItem> sessions;

    @Getter
    @Builder
    public static class SummaryInfo {
        private Long totalTrials;
        private Long successTrials;
        private Double avgAngle;
        private Double inTargetRate;
        private String stabilityLevel;
    }

    @Getter
    @Builder
    public static class SessionItem {
        private Long sessionId;
        private String exerciseName;
        private String goal;
    }
}