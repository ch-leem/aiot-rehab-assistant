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
     * @param rawFrame Redis에서 미리 계산된 통계 요약 JSON 문자열
     */
    @Transactional
    public TryFinishResponse finishTry(Long tryId, String rawFrame) {
        Try t = tryRepository.findById(tryId)
                .orElseThrow(() -> new IllegalArgumentException("Try not found: " + tryId));

        if (t.getEndedAt() != null) {
            throw new IllegalStateException("이미 종료된 운동 시도입니다.");
        }

        // 1. 매핑 정보를 통한 환측(Side) 파악
        Session session = t.getSession();
        Exercise exercise = session.getExercise();
        Patient patient = session.getSequence().getPatient();

        ExercisePatientMapping mapping = mappingRepository.findByPatient_Id(patient.getId()).stream()
                .filter(m -> m.getExercise().getId().equals(exercise.getId()))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Mapping 정보가 없습니다."));

        String side = mapping.getSide().name();

        // 2. 외부 분석기를 통해 계산된 JSON을 DTO로 변환
        // (Redis가 이미 Max, Avg를 계산했으므로 리스트가 아닌 단일 프레임/요약본 처리)
        TryEvaluationRequest evalRequest = frameAnalyzer.analyzeSummary(rawFrame, side);

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

        // Try 엔티티 내부에 totalScore 계산 로직이 있다고 가정
        if (t.getTotalScore() >= SUCCESS_THRESHOLD_PERCENT) {
            t.setResult(TryResult.SUCCESS);
            if (session != null) {
                session.setSuccessTries(session.getSuccessTries() + 1);
            }
        } else {
            t.setResult(TryResult.FAIL);
            // 실패 사유 기본값 설정 (F1)
            t.setFail(failRepository.findById("F1").orElse(null));
        }

        return toResponse(t);
    }

    /**
     * 개별 목표 달성률 계산
     */
    private double calculateAchievement(ExerciseGoal goal, double measured, String side) {
        double target = goal.getTargetValue();
        String name = goal.getName();

        // 수렴형 (특정 수치에 도달해야 함)
        if (name.contains("신전") || name.contains("수평") || name.contains("편차")) {
            double error = Math.abs(target - measured);
            return Math.max(0, 100.0 - (error * (name.contains("신전") ? 2.0 : 5.0)));
        }

        // 안정형 (0에 가까울수록 좋음)
        if (target == 0.0) {
            return Math.max(0, 100.0 - (measured * getPenaltyWeight(name)));
        }

        // 달성형 (타겟 수치 이상이어야 함)
        if (target > 0) {
            double rate = (measured / target) * 100;
            return Math.min(100.0, round1(rate));
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
        return new TryFinishResponse(
                t.getId(),
                t.getTotalScore(),
                t.getResult() != null ? t.getResult().name() : "NONE",
                t.getFail() != null ? t.getFail().getName() : null
        );
    }

    private static double round1(double v) {
        return Math.round(v * 10.0) / 10.0;
    }
}