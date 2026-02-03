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
                            .flatMap(lastSeq ->
                                    // 수정된 레포지토리 메서드 명 호출 (ExerciseId 기반 조회)
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
                    // LLM으로부터 받은 sessionId가 유효한지 검증하고 연관된 Exercise ID 추출
                    // 만약 SessionSummary가 Session 엔티티 자체를 참조한다면 s.getId() 대신 s를 사용하세요.
                    Session session = sessionRepository.findById(es.sessionId())
                            .orElseThrow(() -> new IllegalArgumentException("세션을 찾을 수 없습니다. ID: " + es.sessionId()));

                    return SessionSummary.builder()
                            .sequence(sequence)
                            .session(session)
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

    @Async("reportTaskExecutor")
    @Transactional
    public void createAndSaveReport(Long sequenceId) {
        log.info("비동기 리포트 생성 시작 - Sequence ID: {}, Thread: {}", sequenceId, Thread.currentThread().getName());

        try {
            // 1. 데이터 조립
            PatientRehabReportRequest request = createReportRequest(sequenceId);

            // 2. LLM 분석 요청 (GmsClient 호출 - 내부 block()은 비동기 스레드 안에서 실행되므로 안전)
            PatientRehabReportResponse response = gmsClient.getLlmAnalysis(request);

            // 3. 결과 저장
            saveLlmReportResponse(response);

            log.info("비동기 리포트 생성 및 저장 완료 - Sequence ID: {}", sequenceId);
        } catch (Exception e) {
            log.error("비동기 리포트 생성 중 오류 발생 - Sequence ID: {}", sequenceId, e);
        }
    }

    @Transactional(readOnly = true)
    public PatientRehabReportResponse getSavedReport(Long sequenceId) {
        // 시퀀스 ID로 저장된 리포트 엔티티 조회
        PatientRehabReport report = patientRehabReportRepository.findBySequenceId(sequenceId)
                .orElseThrow(() -> new IllegalArgumentException("해당 시퀀스의 리포트가 존재하지 않습니다. ID: " + sequenceId));

        try {
            // DB에 저장된 JSON 문자열을 다시 Response DTO 객체로 변환하여 반환
            return objectMapper.readValue(report.getFullReportJson(), PatientRehabReportResponse.class);
        } catch (JsonProcessingException e) {
            log.error("JSON 역직렬화 실패", e);
            throw new RuntimeException("리포트 데이터를 읽는 중 오류가 발생했습니다.");
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