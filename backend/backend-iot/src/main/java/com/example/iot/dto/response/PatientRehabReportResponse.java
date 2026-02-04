package com.example.iot.dto.response;

import java.util.List;

/**
 * LLM 분석 서버로부터 수신하는 재활 리포트 응답 데이터 구조
 */
public record PatientRehabReportResponse(
        Long sequenceId,
        String patientName,
        Long patientId,
        String date,
        String rehabPhase,
        String side,
        OverallSummary overallSummary,
        List<ExerciseSummary> exerciseSummaries,
        List<String> riskSignals,
        List<String> nextFocus
) {
    public record OverallSummary(
            String title,
            int totalExercises,
            String overallAssessment
    ) {}

    public record ExerciseSummary(
            Long sessionId,
            String exerciseName,
            Performance performance,
            String summaryTag,         // STABLE | VARIABLE | UNSTABLE
            String withinSessionTrend,       // IMPROVING | STABLE | DECLINING
            String sessionNote,
            List<String> keyObservations,
            ComparisonToPrevious comparisonToPrevious
    ) {}

    public record Performance(
            Double successRate,
            Double averageScore
    ) {}

    public record ComparisonToPrevious(
            boolean used,
            String trend,             // IMPROVING | STABLE | DECLINING | NOT_APPLICABLE
            String trendDescription
    ) {}
}