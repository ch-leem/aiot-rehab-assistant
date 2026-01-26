package com.example.iot.service;

import com.example.iot.domain.*;
import com.example.iot.domain.constant.TryResult;
import com.example.iot.dto.response.TryFinishResponse;
import com.example.iot.dto.response.TryStartResponse;
import com.example.iot.repository.*;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

@Service
@RequiredArgsConstructor // 생성자 주입 생략 가능
public class TryService {

    private static final double SUCCESS_THRESHOLD_PERCENT = 80.0;

    private final TryRepository tryRepository;
    private final SessionRepository sessionRepository;
    private final FailRepository failRepository;
    private final ExerciseGoalRepository exerciseGoalRepository; // 새롭게 추가 필요

    public TryStartResponse startTry(Long tryId) {
        Try t = tryRepository.findById(tryId)
                .orElseThrow(() -> new IllegalArgumentException("Try가 존재하지 않습니다. id=" + tryId));

        t.setStartedAt(LocalDateTime.now());
        return new TryStartResponse(t.getId(), t.getStartedAt());
    }

    @Transactional
    public TryFinishResponse finishTry(Long tryId) {
        Try t = tryRepository.findById(tryId)
                .orElseThrow(() -> new IllegalArgumentException("Try not found: " + tryId));

        if (t.getEndedAt() != null) {
            return toResponse(t, "이미 종료되었습니다.");
        }

        // 1. 해당 운동(Exercise)에 설정된 목표(Goal) 리스트 가져오기
        Exercise exercise = t.getSession().getExercise();
        List<ExerciseGoal> goals = exerciseGoalRepository.findByExercise(exercise);

        double aggregateScore = 0;

        // 2. 각 목표별 결과 계산 및 저장
        for (ExerciseGoal goal : goals) {
            // (나중에 실제 PoseMath/Redis 값으로 대체될 부분)
            double measuredValue = round1(ThreadLocalRandom.current().nextDouble(0, 100));
            double achievementRate = calculateAchievement(goal, measuredValue); // 달성률 계산 로직

            // 상세 결과 엔티티 생성 및 연관관계 편의 메서드 사용
            TryGoalResult result = new TryGoalResult(t, goal, measuredValue, achievementRate);
            t.addGoalResult(result);

            aggregateScore += achievementRate;
        }

        // 3. 종합 점수 계산 (목표 개수로 나눈 평균값 등)
        double totalScore = goals.isEmpty() ? 0 : round1(aggregateScore / goals.size());
        t.setTotalScore(totalScore);
        t.setEndedAt(LocalDateTime.now());

        // 4. 성공/실패 판정
        boolean success = totalScore >= SUCCESS_THRESHOLD_PERCENT;

        if (success) {
            t.setResult(TryResult.SUCCESS);
            t.setFail(null);

            Session s = t.getSession();
            if (s != null) {
                s.setSuccessTries(s.getSuccessTries() + 1);
            }
        } else {
            t.setResult(TryResult.FAIL);
            // 실패 사유 로직 (우선 F1-수동 움직임으로 예시 설정)
            Fail fail = failRepository.findById("F1").orElse(null);
            t.setFail(fail);
        }

        // 5. 피드백 메시지 생성
        String feedbackMsg = generateFeedback(totalScore);

        tryRepository.save(t); // CascadeType.ALL에 의해 TryGoalResult도 함께 저장됨

        return new TryFinishResponse(t.getId(), feedbackMsg);
    }

    // 간단한 달성률 계산 로직 (예: 목표값 대비 비율)
    private double calculateAchievement(ExerciseGoal goal, double measured) {
        // 실제 로직에 맞게 수정 필요 (예: 각도는 작을수록 좋을 수도, 클수록 좋을 수도 있음)
        double rate = (measured / goal.getTargetValue()) * 100;
        return Math.min(100.0, round1(rate));
    }

    private String generateFeedback(double score) {
        if (score >= 90) return "완벽한 자세입니다!";
        if (score >= 80) return "잘하고 계십니다!";
        if (score >= 60) return "조금 더 정확하게 움직여볼까요?";
        return "치료사님의 가이드에 따라 천천히 다시 해보세요.";
    }

    private TryFinishResponse toResponse(Try t, String str) {
        return new TryFinishResponse(t.getId(), str);
    }

    private static double round1(double v) {
        return Math.round(v * 10.0) / 10.0;
    }
}