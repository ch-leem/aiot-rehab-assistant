package com.example.iot.dto.request;

import java.time.LocalDateTime;
import java.util.List;

/**
 * LLM 분석을 위해 전달되는 재활 리포트 요청 데이터 세트
 */
public record PatientRehabReportRequest(
        Long sequenceId,
        Long patientId,
        String patientName,
        String side,
        String rehabPhase,
        LocalDateTime date,
        List<RehabSessionSummary> sessions
) {
    public record RehabSessionSummary(
            Long sessionId,
            String exerciseName,
            PreviousSessionContext previousSessionContext, // 세션별 이전 문맥 (기록 없을 시 null)
            int totalTries,
            int successTries,
            Double sessionAvgScore,
            List<RehabTryDetail> tries
    ) {}

    public record PreviousSessionContext(
            LocalDateTime lastSessionDate,
            Double lastSessionAvgScore,
            Double lastSessionMainGoalRate,
            String lastSessionNote
    ) {
        // 이전 기록이 없을 경우
        public static PreviousSessionContext empty() {
            return new PreviousSessionContext(
                    null,
                    0.0,
                    0.0,
                    "이전 기록이 없습니다"
            );
        }
    }

    public record RehabTryDetail(
            int tryOrder,
            Double totalScore,
            String resultStatus,
            String failName,
            List<RehabGoalResult> goalResults
    ) {}

    public record RehabGoalResult(
            String goalName,
            String goalType,    // MAIN / SUB
            Double measuredValue,
            Double targetValue,
            Double achievementRate
    ) {}
}