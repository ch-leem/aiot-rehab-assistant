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

        // 2. 1:1 관계인 SessionSummary 조회 (@MapsId 구조이므로 sequenceId로 직접 조회 가능)
        SessionSummary summary = summaryRepository.findById(sequenceId).orElse(null);

        // 3. 해당 시퀀스에 속한 세션(운동) 리스트 조회
        // 엔티티에 세션 리스트 역참조가 없으므로 Repository를 통해 sequence_id로 필터링
        // (실제 서비스에서는 sessionRepository에 findBySequence_Id 커스텀 메서드를 작성하는 것이 성능상 유리합니다)
        List<Session> sessions = sessionRepository.findAll().stream()
                .filter(s -> s.getSequence().getId().equals(sequenceId))
                .toList();

        return SequenceDetailResponse.builder()
                .sequenceId(sequence.getId())
                .feedback(sequence.getFeedback())
                .summary(mapToSummaryInfo(summary))
                .sessions(sessions.stream()
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
                .totalTrials(summary.getTotalTrials())
                .successTrials(summary.getSuccessTrials())
                .avgAngle(summary.getAvgAngle())
                .inTargetRate(summary.getInTargetRate())
                .stabilityLevel(summary.getStabilityLevel())
                .build();
    }

    /**
     * Session 엔티티를 DTO 내부의 리스트 아이템 객체로 변환
     */
    private SequenceDetailResponse.SessionItem mapToSessionItem(Session session) {
        return SequenceDetailResponse.SessionItem.builder()
                .sessionId(session.getId())
                .exerciseName(session.getExercise().getName()) // Exercise 정보 포함
                .goal(session.getGoal())
                .build();
    }
}