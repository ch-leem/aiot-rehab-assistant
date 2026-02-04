package com.example.user.service;

import com.example.iot.domain.Sequence;
import com.example.iot.domain.Session;
import com.example.iot.domain.SessionSummary;
import com.example.iot.repository.SequenceRepository;
import com.example.iot.repository.SessionRepository;
import com.example.iot.repository.SessionSummaryRepository;
import com.example.user.dto.SequenceDetailResponse;
import com.example.user.dto.SequenceResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true) // 조회 성능 최적화 및 DB 락 방지
public class SequenceService {

    private final SequenceRepository sequenceRepository;
    private final SessionSummaryRepository summaryRepository;
    private final SessionRepository sessionRepository;

    /**
     * 특정 환자의 모든 재활 기록 목록 조회 (최신순)
     */
    public List<SequenceResponse> getPatientSequences(Long patientId) {
        return sequenceRepository.findByPatient_IdOrderByStartedAtDesc(patientId)
                .stream()
                .map(SequenceResponse::from)
                .collect(Collectors.toList());
    }

    /**
     * 특정 재활 회차(Sequence)의 상세 정보 조회
     * (요약 통계 및 포함된 세션 리스트 결합)
     */
    public SequenceDetailResponse getSequenceDetail(Long sequenceId) {
        // 1. Sequence 기본 정보 조회
        Sequence sequence = sequenceRepository.findById(sequenceId)
                .orElseThrow(() -> new IllegalArgumentException("해당 재활 기록을 찾을 수 없습니다. ID: " + sequenceId));

        // 2. 해당 시퀀스의 모든 요약 리스트를 가져옵니다.
        List<SessionSummary> summaryEntities = summaryRepository.findAllBySequenceId(sequenceId);

        // 3. 해당 시퀀스에 속한 세션 리스트 조회
        List<Session> sessionEntities = sessionRepository.findAllDetailBySequenceId(sequenceId);

        return SequenceDetailResponse.builder()
                .sequenceId(sequence.getId())
                .feedback(sequence.getFeedback())
                // 3. [변경] DTO 필드명이 summaries(List)이므로 map을 통해 변환하여 전달
                .summaries(summaryEntities.stream()
                        .map(this::mapToSummaryInfo)
                        .collect(Collectors.toList()))
                // 4. 세션 아이템 매핑 (시도 횟수 포함)
                .sessions(sessionEntities.stream()
                        .map(this::mapToSessionItem)
                        .collect(Collectors.toList()))
                .build();
    }

    /**
     * SessionSummary 엔티티를 DTO 내부의 요약 정보 객체로 변환
     */
    private SequenceDetailResponse.SummaryInfo mapToSummaryInfo(SessionSummary summary) {
        if (summary == null) return null;

        return SequenceDetailResponse.SummaryInfo.builder()
                .exerciseId(summary.getSession().getExercise().getId())
                .successRate(summary.getSuccessRate())
                .averageScore(summary.getAverageScore())
                .summaryTag(summary.getSummaryTag())
                .sessionNote(summary.getSessionNote())
                .build();
    }

    /**
     * Session 엔티티를 DTO 내부의 리스트 아이템 객체로 변환
     */
    private SequenceDetailResponse.SessionItem mapToSessionItem(Session session) {
        return SequenceDetailResponse.SessionItem.builder()
                .sessionId(session.getId())
                .exerciseName(session.getExercise().getName())
                .goal(session.getGoal())
                .totalTries(session.getTotalTries())
                .successTries(session.getSuccessTries())
                .build();
    }
}