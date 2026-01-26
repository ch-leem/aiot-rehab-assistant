package com.example.user.dto;

import lombok.Builder;
import lombok.Getter;
import java.time.LocalDateTime;
import java.util.List;

@Getter
@Builder
public class SessionDetailResponse {
    private Long sessionId;
    private String exerciseName;
    private String goal;
    private List<TryItem> tries;

    @Getter
    @Builder
    public static class TryItem {
        private Long tryId;
        private LocalDateTime startedAt;
        private LocalDateTime endedAt;
        private Double totalScore;
        private boolean isSuccess;
        private String failName;
        private String failDescription;

        // 상세 목표 결과 리스트 추가
        private List<GoalDetailDto> goalDetails;
    }

    @Getter
    @Builder
    public static class GoalDetailDto {
        private String name;
        private Double measured;
        private Double target;
        private String unit;
    }
}