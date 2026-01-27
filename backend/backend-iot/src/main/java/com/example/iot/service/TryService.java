package com.example.iot.service;

import com.example.iot.domain.*;
import com.example.iot.domain.constant.TryResult;
import com.example.iot.dto.request.TryEvaluationRequest;
import com.example.iot.dto.response.TryFinishResponse;
import com.example.iot.dto.response.TryStartResponse;
import com.example.iot.repository.*;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class TryService {

    private static final double SUCCESS_THRESHOLD_PERCENT = 80.0;

    private final TryRepository tryRepository;
    private final FailRepository failRepository;
    private final ExerciseGoalRepository exerciseGoalRepository;
    private final ExercisePatientMappingRepository mappingRepository;
    private final FrameAnalyzer frameAnalyzer; // 분석기 주입

    @Transactional
    public TryStartResponse startTry(Long tryId) {
        Try t = tryRepository.findById(tryId)
                .orElseThrow(() -> new IllegalArgumentException("Try가 존재하지 않습니다. id=" + tryId));
        t.setStartedAt(LocalDateTime.now());
        return new TryStartResponse(t.getId(), t.getStartedAt());
    }

    /**
     * @param rawFrames Redis 등 외부에서 조회해온 JSON 문자열 리스트
     */
    @Transactional
    public TryFinishResponse finishTry(Long tryId, List<String> rawFrames) {
        Try t = tryRepository.findById(tryId)
                .orElseThrow(() -> new IllegalArgumentException("Try not found: " + tryId));

        if (t.getEndedAt() != null) {
            throw new IllegalStateException("이미 종료된 운동 시도입니다.");
        }

        // 1. 매핑 정보를 통한 환측(Side) 파악
        Exercise exercise = t.getSession().getExercise();
        Patient patient = t.getSession().getSequence().getPatient();
        ExercisePatientMapping mapping = mappingRepository.findByPatient_Id(patient.getId()).stream()
                .filter(m -> m.getExercise().getId().equals(exercise.getId()))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Mapping 정보가 없습니다."));

        String side = mapping.getSide().name();

        // 2. 외부 분석기를 통한 데이터 통계화 (Redis 경로 의존성 없음)
        TryEvaluationRequest evalRequest = frameAnalyzer.analyze(rawFrames, side);

        // 3. 목표별 점수 산출 및 저장
        List<ExerciseGoal> goals = exerciseGoalRepository.findByExercise(exercise);
        for (ExerciseGoal goal : goals) {
            double measuredValue = evalRequest.getValueByGoalName(goal.getName());
            double achievementRate = calculateAchievement(goal, measuredValue, side);

            TryGoalResult result = new TryGoalResult(t, goal, measuredValue, achievementRate);
            t.addGoalResult(result);
        }

        // 4. 최종 결과 확정
        t.setEndedAt(LocalDateTime.now());
        if (t.getTotalScore() >= SUCCESS_THRESHOLD_PERCENT) {
            t.setResult(TryResult.SUCCESS);
            if (t.getSession() != null) {
                t.getSession().setSuccessTries(t.getSession().getSuccessTries() + 1);
            }
        } else {
            t.setResult(TryResult.FAIL);
            t.setFail(failRepository.findById("F1").orElse(null));
        }

        return toResponse(t);
    }

    private double calculateAchievement(ExerciseGoal goal, double measured, String side) {
        double target = goal.getTargetValue();
        String name = goal.getName();

        if (name.contains("신전") || name.contains("수평") || name.contains("편차")) {
            double error = Math.abs(target - measured);
            return Math.max(0, 100.0 - (error * (name.contains("신전") ? 2.0 : 5.0)));
        }

        if (target == 0.0) {
            return Math.max(0, 100.0 - (measured * getPenaltyWeight(name)));
        }

        if (target > 0) {
            return Math.min(100.0, (measured / target) * 100);
        }
        return 0.0;
    }

    private double getPenaltyWeight(String name) {
        return switch (name) {
            case "상체 앞뒤 기울기", "상체 앞뒤 기울임" -> 5.0;
            case "수행 가속도" -> 20.0;
            case "비마비측 발목 흔들림" -> 10.0;
            default -> 1.0;
        };
    }

    private TryFinishResponse toResponse(Try t) {
        return new TryFinishResponse(t.getId(), t.getTotalScore(),
                t.getResult() != null ? t.getResult().name() : "NONE",
                t.getFail() != null ? t.getFail().getName() : null);
    }
}