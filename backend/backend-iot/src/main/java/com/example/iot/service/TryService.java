package com.example.iot.service;

import com.example.iot.domain.*;
import com.example.iot.domain.constant.TryResult;
import com.example.iot.dto.request.TryEvaluationRequest;
import com.example.iot.dto.response.TryFinishResponse;
import com.example.iot.dto.response.TryStartResponse;
import com.example.iot.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class TryService {

    private static final double SUCCESS_THRESHOLD_PERCENT = 70.0;

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
     * @param tryId    : 시도 ID
     * @param rawFrame : Redis 'latest' 키에서 가져온 최신 JSON 문자열
     * @param agg      : Redis 'agg' 키(Hash)에서 가져온 집계 데이터 Map
     */
    @Transactional
    public TryFinishResponse finishTry(Long tryId, String rawFrame, Map<Object, Object> agg) {
        Try t = tryRepository.findById(tryId)
                .orElseThrow(() -> new IllegalArgumentException("Try not found: " + tryId));

        if (t.getEndedAt() != null) {
            throw new IllegalStateException("이미 종료된 운동 시도입니다.");
        }

        // 1. 환자 및 운동 정보 파악 (측측 side 결정)
        Session session = t.getSession();
        Exercise exercise = session.getExercise();
        Patient patient = session.getSequence().getPatient();

        ExercisePatientMapping mapping = mappingRepository.findByPatient_Id(patient.getId()).stream()
                .filter(m -> m.getExercise().getId().equals(exercise.getId()))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Mapping 정보가 없습니다."));

        String side = mapping.getSide().name(); // "LEFT" or "RIGHT"

        // 2. 분석기를 통해 통계 데이터를 DTO로 변환 (agg 데이터 전달)
        TryEvaluationRequest evalRequest = frameAnalyzer.analyzeSummary(rawFrame, agg, side);

        // 3. 목표별 점수 산출 및 저장
        List<ExerciseGoal> goals = exerciseGoalRepository.findByExercise(exercise);
        for (ExerciseGoal goal : goals) {
            // DTO 내부의 getValueByGoalName을 사용하여 목표에 맞는 수치(Avg/Max) 추출
            double measuredValue = evalRequest.getValueByGoalName(goal.getName());
            double achievementRate = calculateAchievement(goal, measuredValue);

            TryGoalResult result = new TryGoalResult(t, goal, measuredValue, achievementRate);
            t.addGoalResult(result);
        }

        // 4. 최종 결과 확정 및 성공 여부 판정
        t.setEndedAt(LocalDateTime.now());

        if (t.getTotalScore() >= SUCCESS_THRESHOLD_PERCENT) {
            t.setResult(TryResult.SUCCESS);
            if (session != null) {
                session.setSuccessTries(session.getSuccessTries() + 1);
            }
        } else {
            t.setResult(TryResult.FAIL);
            t.setFail(failRepository.findById("F1").orElse(null));
        }

        return toResponse(t);
    }

    /**
     * 개별 목표 달성률 계산
     */
    private double calculateAchievement(ExerciseGoal goal, double measured) {
        double target = goal.getTargetValue();
        String name = goal.getName();
        double rawScore; // 계산된 원본 점수

        // 1. [안정형 & 수렴형 통합] 기준점(Target)을 중심으로 안정을 유지해야 하는 경우
        // 골반 수평 편차, 어깨 수평 불균형, 상체 앞뒤 기울기 등
        if (target == 0.0 || name.contains("수평") || name.contains("편차") || name.contains("기울기")) {
            // 기준점과의 절대 오차 계산 (예: 180도 기준이면 |180 - measured|)
            double error = Math.abs(target - measured);
            rawScore = 100.0 - (error * getPenaltyWeight(name));
        }

        // 2. [달성형] 타겟 수치 이상이어야 함 (최대 압력, 신전 각도 등)
        else if (target > 0) {
            if (measured <= 0) return 0.0;
            double rate = (measured / target) * 100;
            rawScore = round1(rate);
        }

        // 3. 예외 케이스
        else {
            rawScore = 0.0;
        }

        // 최종 점수 제한 (0~100)
        return Math.max(0.0, Math.min(100.0, rawScore));
    }

    private double getPenaltyWeight(String name) {
        return switch (name) {
            case "골반 수평 편차", "어깨 수평 불균형" -> 2.0;
            case "상체 앞뒤 기울기" -> 5.0;
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