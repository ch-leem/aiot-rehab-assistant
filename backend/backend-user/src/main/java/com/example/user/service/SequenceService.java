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
@Transactional(readOnly = true)
public class SequenceService {

    private final SequenceRepository sequenceRepository;
    private final SessionSummaryRepository summaryRepository; // 리포트 요약용
    private final SessionRepository sessionRepository;

    public List<SequenceResponse> getPatientSequences(Long patientId) {
        return sequenceRepository.findByPatient_IdOrderByStartedAtDesc(patientId)
                .stream()
                .map(SequenceResponse::from)
                .collect(Collectors.toList());
    }

    public SequenceDetailResponse getSequenceDetail(Long sequenceId) {
        // 1. Sequence 기본 정보 조회
        Sequence sequence = sequenceRepository.findById(sequenceId)
                .orElseThrow(() -> new IllegalArgumentException("해당 재활 기록을 찾을 수 없습니다. ID: " + sequenceId));

        // 2. 해당 시퀀스의 모든 운동 요약 리스트 조회 (1:N 반영)
        // 시퀀스 ID로 해당 회차에 생성된 모든 세션 요약들을 가져옵니다.
        List<SessionSummary> summaries = summaryRepository.findAllBySequenceId(sequenceId);

        // 3. 해당 시퀀스에 속한 세션 리스트 조회 (최적화된 쿼리 사용)
        List<Session> sessions = sessionRepository.findBySequence_IdOrderByStartedAtAsc(sequenceId);

        return SequenceDetailResponse.builder()
                .sequenceId(sequence.getId())
                .feedback(sequence.getFeedback())
                .summaries(summaries.stream() // 리스트 형태로 변경 권장
                        .map(this::mapToSummaryInfo)
                        .collect(Collectors.toList()))
                .sessions(sessions.stream()
                        .map(this::mapToSessionItem)
                        .collect(Collectors.toList()))
                .build();
    }

    /**
     * [수정] SessionSummary 엔티티의 실제 필드(AI 분석 결과)에 맞게 매핑
     */
    private SequenceDetailResponse.SummaryInfo mapToSummaryInfo(SessionSummary summary) {
        if (summary == null) return null;

        return SequenceDetailResponse.SummaryInfo.builder()
                .exerciseId(summary.getExerciseId())
                .successRate(summary.getSuccessRate())    // 기존 inTargetRate 대체
                .averageScore(summary.getAverageScore())  // 기존 avgAngle 대체
                .summaryTag(summary.getSummaryTag())      // 기존 stabilityLevel 대체
                .sessionNote(summary.getSessionNote())    // 추가된 분석 필드
                .build();
    }

    private SequenceDetailResponse.SessionItem mapToSessionItem(Session session) {
        return SequenceDetailResponse.SessionItem.builder()
                .sessionId(session.getId())
                .exerciseName(session.getExercise().getName())
                .goal(session.getGoal())
                .totalTries(session.getTotalTries())     // 엔티티에 있는 필드 활용
                .successTries(session.getSuccessTries()) // 엔티티에 있는 필드 활용
                .build();
    }
}