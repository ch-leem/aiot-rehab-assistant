package com.example.iot.service;

import com.example.iot.client.GmsClient;
import com.example.iot.domain.*;
import com.example.iot.dto.request.PatientRehabReportRequest;
import com.example.iot.dto.response.PatientRehabReportResponse;
import com.example.iot.repository.*;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Objects;
import java.util.Optional;

@Slf4j
@Service
@RequiredArgsConstructor
public class PatientRehabReportService {

    private final SequenceRepository sequenceRepository;
    private final SessionRepository sessionRepository;
    private final SessionSummaryRepository sessionSummaryRepository;
    private final PatientRehabReportRepository patientRehabReportRepository;
    private final ExercisePatientMappingRepository mappingRepository;
    private final GmsClient gmsClient;
    private final ObjectMapper objectMapper;

    /**
     * 1. LLM 분석용 요청 데이터 조립
     */
    @Transactional(readOnly = true)
    public PatientRehabReportRequest createReportRequest(Long sequenceId) {
        Sequence sequence = sequenceRepository.findById(sequenceId)
                .orElseThrow(() -> new IllegalArgumentException("시퀀스를 찾을 수 없습니다. ID: " + sequenceId));
        Patient patient = sequence.getPatient();

        // [Fetch Join 활용] 세션 내 Tries와 GoalResults를 한 번에 긁어와 N+1 문제 방지
        List<Session> sessions = sessionRepository.findAllDetailBySequenceId(sequenceId);

        Optional<Sequence> lastSequence = sequenceRepository.findFirstByPatientIdAndIdLessThanOrderByIdDesc(patient.getId(), sequenceId);

        String sideValue = "N/A";
        if (!sessions.isEmpty()) {
            // [Repository 메서드 일치] findByPatient_IdAndExercise_Id 호출
            sideValue = mappingRepository.findByPatient_IdAndExercise_Id(patient.getId(), sessions.get(0).getExercise().getId())
                    .map(mapping -> mapping.getSide().name())
                    .orElse("N/A");
        }

        // [RehabPhase 조회] Patient 엔티티의 Enum 값 추출
        String phaseValue = (patient.getRehabPhase() != null) ? patient.getRehabPhase().name() : "PHASE_UNKNOWN";

        List<PatientRehabReportRequest.RehabSessionSummary> sessionDtos = sessions.stream()
                .map(session -> {
                    // 세션별 이전 기록 문맥 조립
                    PatientRehabReportRequest.PreviousSessionContext prevContext = lastSequence
                            .flatMap(lastSeq ->
                                    sessionSummaryRepository.findBySequenceIdAndSession_Exercise_Id(
                                            lastSeq.getId(),
                                            session.getExercise().getId()
                                    )
                            )
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
                                    t.getFail() != null ? t.getFail().getName() : null,
                                    t.getGoalResults().stream()
                                            .map(gr -> new PatientRehabReportRequest.RehabGoalResult(
                                                    gr.getExerciseGoal().getName(),
                                                    gr.getExerciseGoal().getGoalType(),
                                                    gr.getMeasuredValue(),
                                                    gr.getExerciseGoal().getTargetValue(),
                                                    gr.getAchievementRate()
                                            )).toList()
                            )).toList();

                    Double sessionAvgScore = tryDetails.stream()
                            .map(PatientRehabReportRequest.RehabTryDetail::totalScore)
                            .filter(Objects::nonNull) // null 값 필터링
                            .mapToDouble(Double::doubleValue) // 안전하게 double로 변환
                            .average()
                            .orElse(0.0);

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
                .orElseThrow(() -> new IllegalArgumentException("시퀀스를 찾을 수 없습니다. ID: " + response.sequenceId()));

        // 1. 메인 리포트 테이블 저장
        PatientRehabReport report = PatientRehabReport.builder()
                .sequence(sequence)
                .overallTitle(response.overallSummary().title())
                .overallAssessment(response.overallSummary().overallAssessment())
                .fullReportJson(serializeToJson(response))
                .build();
        patientRehabReportRepository.save(report);

        // 2. 세션별 요약 테이블 저장 (DTO에 추가된 sessionId 활용)
        List<SessionSummary> summaries = response.exerciseSummaries().stream()
                .map(es -> {
                    Session session = sessionRepository.findById(es.sessionId())
                            .orElseThrow(() -> new IllegalArgumentException("세션을 찾을 수 없습니다. ID: " + es.sessionId()));

                    return SessionSummary.builder()
                            .sequence(sequence)
                            .session(session)
                            .successRate(es.performance().successRate())
                            .averageScore(es.performance().averageScore())
                            .summaryTag(es.summaryTag())
                            .sessionTrend(es.withinSessionTrend()) // JSON의 withinSessionTrend 매핑
                            .sessionNote(es.sessionNote())
                            .trend(es.comparisonToPrevious().trend())
                            .trendDescription(es.comparisonToPrevious().trendDescription())
                            .build();
                }).toList();

        sessionSummaryRepository.saveAll(summaries);
    }

    @Async("reportTaskExecutor")
    @Transactional
    public void createAndSaveReport(Long sequenceId) {
        log.info("비동기 리포트 생성 시작 - Sequence ID: {}", sequenceId);

        try {
            // 1. 데이터 조립 전 로그
            log.info("1. 리포트 데이터 조립 시작...");
            PatientRehabReportRequest request = createReportRequest(sequenceId);
            log.info("2. 데이터 조립 완료. GMS 호출 시도 (Patient: {})", request.patientName());

            // 2. GMS 호출
            PatientRehabReportResponse response = gmsClient.getLlmAnalysis(request);
            log.info("3. GMS 응답 수신 성공. DB 저장 시작...");

            // 3. 결과 저장
            saveLlmReportResponse(response);
            log.info("== [REPORT ASYNC SUCCESS] Sequence ID: {} ==", sequenceId);
        } catch (Exception e) {
            log.error("!! [REPORT ASYNC FAILED] Sequence ID: {} - Error: {}", sequenceId, e.getMessage(), e);
        }
    }

    @Transactional(readOnly = true)
    public PatientRehabReportResponse getSavedReport(Long sequenceId) {
        PatientRehabReport report = patientRehabReportRepository.findBySequenceId(sequenceId)
                .orElseThrow(() -> new IllegalArgumentException("리포트가 존재하지 않습니다."));
        try {
            return objectMapper.readValue(report.getFullReportJson(), PatientRehabReportResponse.class);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("JSON 역직렬화 실패", e);
        }
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