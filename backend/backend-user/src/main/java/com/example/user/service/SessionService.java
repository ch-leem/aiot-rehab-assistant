package com.example.user.service;

import com.example.iot.domain.Session;
import com.example.iot.domain.Try;
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
        // 1. 세션 기본 정보 및 운동 정보 조회
        Session session = sessionRepository.findById(sessionId)
                .orElseThrow(() -> new IllegalArgumentException("세션을 찾을 수 없습니다. ID: " + sessionId));

        // 2. 해당 세션에 속한 모든 시도(Try) 조회
        // 현재는 전체 조회 후 필터링하지만, 나중에 TryRepository에 findBySession_Id를 추가하는 것이 좋습니다.
        List<Try> tries = tryRepository.findAll().stream()
                .filter(t -> t.getSession().getId().equals(sessionId))
                .toList();

        return SessionDetailResponse.builder()
                .sessionId(session.getId())
                .exerciseName(session.getExercise().getName())
                .goal(session.getGoal())
                .tries(tries.stream().map(this::mapToTryItem).collect(Collectors.toList()))
                .build();
    }

    private SessionDetailResponse.TryItem mapToTryItem(Try tryEntity) {
        // fail이 null이면 성공, 아니면 실패로 판단
        boolean isSuccess = (tryEntity.getFail() == null);

        return SessionDetailResponse.TryItem.builder()
                .tryId(tryEntity.getId())
                .startedAt(tryEntity.getStartedAt())
                .endedAt(tryEntity.getEndedAt())
                .goalSensor(tryEntity.getGoalSensor())
                .goalVision(tryEntity.getGoalVision())
                .isSuccess(isSuccess)
                .failName(!isSuccess ? tryEntity.getFail().getName() : null)
                .failDescription(!isSuccess ? tryEntity.getFail().getDescription() : null)
                .build();
    }
}