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
        private String goalSensor;
        private String goalVision;
        private boolean isSuccess;
        private String failName; // Fail 엔티티에서 가져옴
        private String failDescription;
    }
}