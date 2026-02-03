package com.example.iot.service;

import com.example.iot.domain.*;
import com.example.iot.dto.request.PatientRehabReportRequest;
import com.example.iot.dto.response.PatientRehabReportResponse;
import com.example.iot.repository.*;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Slf4j
@Service
@RequiredArgsConstructor
public class PatientRehabReportService {

    private final SequenceRepository sequenceRepository;
    private final SessionRepository sessionRepository;
    private final SessionSummaryRepository sessionSummaryRepository;
    private final PatientRehabReportRepository patientRehabReportRepository;
    private final ExercisePatientMappingRepository mappingRepository; // 추가
    private final ObjectMapper objectMapper;

    /**
     * 1. LLM 분석용 요청 데이터 조립
     */
    @Transactional(readOnly = true)
    public PatientRehabReportRequest createReportRequest(Long sequenceId) {
        Sequence sequence = sequenceRepository.findById(sequenceId)
                .orElseThrow(() -> new IllegalArgumentException("시퀀스를 찾을 수 없습니다. ID: " + sequenceId));
        Patient patient = sequence.getPatient();

        // 시퀀스 내 모든 세션 조회 (fetch join을 통해 tries와 goalResults를 포함한 리스트 권장)
        List<Session> sessions = sessionRepository.findAllDetailBySequenceId(sequenceId);

        // 이전 문맥 조회를 위한 직전 시퀀스 탐색
        Optional<Sequence> lastSequence = sequenceRepository.findLastSequence(patient.getId(), sequenceId);

        // [Side 조회] 시퀀스의 첫 번째 세션 운동을 기준으로 매핑 테이블에서 Side(Enum) 추출
        String sideValue = "N/A";
        if (!sessions.isEmpty()) {
            sideValue = mappingRepository.findByPatientIdAndExerciseId(patient.getId(), sessions.get(0).getExercise().getId())
                    .map(mapping -> mapping.getSide().name()) // Enum -> String
                    .orElse("N/A");
        }

        // [RehabPhase 조회] Patient 엔티티의 Enum 값 추출
        String phaseValue = (patient.getRehabPhase() != null) ? patient.getRehabPhase().name() : "PHASE_UNKNOWN";

        List<PatientRehabReportRequest.RehabSessionSummary> sessionDtos = sessions.stream()
                .map(session -> {
                    // 세션별 이전 기록 문맥 조립
                    PatientRehabReportRequest.PreviousSessionContext prevContext = lastSequence
                            .flatMap(lastSeq -> sessionSummaryRepository.findBySequenceIdAndExerciseId(lastSeq.getId(), session.getExercise().getId()))
                            .map(summary -> new PatientRehabReportRequest.PreviousSessionContext(
                                    summary.getSequence().getEndedAt(),
                                    summary.getAverageScore(),
                                    summary.getSuccessRate(),
                                    summary.getSessionNote()
                            ))
                            .orElse(PatientRehabReportRequest.PreviousSessionContext.empty());

                    // 세션 내 시도(Try) 리스트 조립
                    List<PatientRehabReportRequest.RehabTryDetail> tryDetails = session.getTries().stream()
                            .map(t -> new PatientRehabReportRequest.RehabTryDetail(
                                    0, // 순번 필드 부재 시 0
                                    t.getTotalScore(),
                                    t.getResult() != null ? t.getResult().name() : "UNKNOWN",
                                    t.getFail() != null ? t.getFail().getName() : null, // Fail 엔티티: name
                                    t.getGoalResults().stream()
                                            .map(gr -> new PatientRehabReportRequest.RehabGoalResult(
                                                    gr.getExerciseGoal().getName(),       // ExerciseGoal: name
                                                    gr.getExerciseGoal().getGoalType(),   // ExerciseGoal: goalType (String)
                                                    gr.getMeasuredValue(),                // TryGoalResult: measuredValue
                                                    gr.getExerciseGoal().getTargetValue(), // ExerciseGoal: targetValue
                                                    gr.getAchievementRate()               // TryGoalResult: achievementRate
                                            )).toList()
                            )).toList();

                    Double sessionAvgScore = tryDetails.stream()
                            .mapToDouble(PatientRehabReportRequest.RehabTryDetail::totalScore)
                            .average().orElse(0.0);

                    return new PatientRehabReportRequest.RehabSessionSummary(
                            session.getId(),
                            session.getExercise().getName(),
                            prevContext,
                            session.getTotalTries(),
                            session.getSuccessTries(),
                            sessionAvgScore,
                            tryDetails
                    );
                }).toList();

        return new PatientRehabReportRequest(
                sequence.getId(),
                patient.getId(),
                patient.getName(),
                sideValue,
                phaseValue,
                LocalDateTime.now(),
                sessionDtos
        );
    }

    /**
     * 2. LLM 응답 결과 저장
     */
    @Transactional
    public void saveLlmReportResponse(PatientRehabReportResponse response) {
        Sequence sequence = sequenceRepository.findById(response.sequenceId())
                .orElseThrow(() -> new IllegalArgumentException("시퀀스를 찾을 수 없습니다."));

        // 메인 리포트 테이블 저장
        PatientRehabReport report = PatientRehabReport.builder()
                .sequence(sequence)
                .overallTitle(response.overallSummary().title())
                .overallAssessment(response.overallSummary().overallAssessment())
                .fullReportJson(serializeToJson(response))
                .build();
        patientRehabReportRepository.save(report);

        // 세션별 요약 테이블 저장 (다음 세션의 Context로 활용됨)
        List<SessionSummary> summaries = response.exerciseSummaries().stream()
                .map(es -> {
                    Long exerciseId = sessionRepository.findBySequenceIdWithExercise(sequence.getId()).stream()
                            .filter(s -> s.getExercise().getName().equals(es.exerciseName()))
                            .map(s -> s.getExercise().getId())
                            .findFirst()
                            .orElse(0L);

                    return SessionSummary.builder()
                            .sequence(sequence)
                            .exerciseId(exerciseId)
                            .successRate(es.performance().successRate())
                            .averageScore(es.performance().averageScore())
                            .summaryTag(es.summaryTag())
                            .sessionTrend(es.sessionTrend())
                            .sessionNote(es.sessionNote())
                            .trend(es.comparisonToPrevious().trend())
                            .trendDescription(es.comparisonToPrevious().trendDescription())
                            .build();
                }).toList();

        sessionSummaryRepository.saveAll(summaries);
    }

    private String serializeToJson(Object obj) {
        try {
            return objectMapper.writeValueAsString(obj);
        } catch (JsonProcessingException e) {
            log.error("JSON serialization error", e);
            return "{}";
        }
    }
}