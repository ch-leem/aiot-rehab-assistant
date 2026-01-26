package com.example.user.service;

import com.example.iot.domain.Session;
import com.example.iot.domain.Try;
import com.example.iot.domain.TryGoalResult; // 추가
import com.example.iot.repository.SessionRepository;
import com.example.iot.repository.TryRepository;
import com.example.user.dto.SessionDetailResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class SessionService {

    private final SessionRepository sessionRepository;
    private final TryRepository tryRepository;

    public SessionDetailResponse getSessionDetail(Long sessionId) {
        Session session = sessionRepository.findById(sessionId)
                .orElseThrow(() -> new IllegalArgumentException("세션을 찾을 수 없습니다. ID: " + sessionId));

        // 최적화: tryRepository에 findBySessionId 메서드를 추가해서 사용하는 것을 권장합니다.
        List<Try> tries = tryRepository.findBySessionId(sessionId);

        return SessionDetailResponse.builder()
                .sessionId(session.getId())
                .exerciseName(session.getExercise().getName())
                .goal(session.getGoal())
                .tries(tries.stream().map(this::mapToTryItem).collect(Collectors.toList()))
                .build();
    }

    private SessionDetailResponse.TryItem mapToTryItem(Try tryEntity) {
        // 1. 성공 여부 판단 (Result Enum 기준)
        boolean isSuccess = (tryEntity.getResult() == com.example.iot.domain.constant.TryResult.SUCCESS);

        // 2. TryGoalResult 엔티티 리스트 -> GoalDetailDto 리스트 변환
        List<SessionDetailResponse.GoalDetailDto> goalDetails = tryEntity.getGoalResults().stream()
                .map(gr -> SessionDetailResponse.GoalDetailDto.builder()
                        .name(gr.getExerciseGoal().getName())
                        .measured(gr.getMeasuredValue())
                        .target(gr.getExerciseGoal().getTargetValue())
                        .unit(gr.getExerciseGoal().getUnit())
                        .build())
                .collect(Collectors.toList());

        return SessionDetailResponse.TryItem.builder()
                .tryId(tryEntity.getId())
                .startedAt(tryEntity.getStartedAt())
                .endedAt(tryEntity.getEndedAt())
                .totalScore(tryEntity.getTotalScore())
                .isSuccess(isSuccess)
                .goalDetails(goalDetails) // 변환한 리스트 주입
                .failName(!isSuccess && tryEntity.getFail() != null ? tryEntity.getFail().getName() : null)
                .failDescription(!isSuccess && tryEntity.getFail() != null ? tryEntity.getFail().getFailDescription() : null)
                .build();
    }
}