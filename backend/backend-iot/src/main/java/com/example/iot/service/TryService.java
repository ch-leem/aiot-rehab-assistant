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

        double minScore = 101.0;      // 비교를 위해 만점보다 높은 값으로 초기화
        String worstGoalName = "";    // 가장 점수가 낮은 목표의 이름을 저장

        for (ExerciseGoal goal : goals) {
            double measuredValue = evalRequest.getValueByGoalName(goal.getName());

            double finalTarget = getFinalTargetValue(goal, patient);

            double achievementRate = calculateAchievement(goal, measuredValue, finalTarget);

            if (achievementRate < minScore) {
                minScore = achievementRate;
                worstGoalName = goal.getName();
            }

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
            String failId = mapGoalNameToFailId(worstGoalName);
            t.setFail(failRepository.findById(failId).orElse(null));
        }

        return toResponse(t);
    }

    /**
     * 개별 목표 달성률 계산
     */
    private double calculateAchievement(ExerciseGoal goal, double measured, double finalTarget) {
        String name = goal.getName();
        double rawScore;

        rawScore = switch (name) {

            // [안정형/유지형] 기준값(Target)과의 편차를 측정 (180도 보정 포함)
            case "상체 앞뒤 기울기", "어깨 수평 불균형", "골반 수평 편차", "팔꿈치 신전 상태" -> {
                double normalizedMeasured = (measured % 360 + 360) % 360;
                double error = Math.abs(180.0 - normalizedMeasured);
                yield 100.0 - (error * getPenaltyWeight(name));
            }

            // [기준유지형] 특정 수치(가속도 등)를 일정하게 유지해야 하는 경우
            case "수행 가속도" -> {
                // measured: 실제 가속도/속도/파워 값 (frameAnalyzer에서 만든 값)
                // finalTarget: 목표 (예: 목표 가속도)
                double ratio = measured / finalTarget; // 1.0이면 딱 목표

                // 1) 허용 구간(10% 이내는 그냥 성공으로 봄)
                double tol = 0.10; // 10%
                double diff = Math.abs(ratio - 1.0);

                if (diff <= tol) {
                    yield 100.0;
                }

                // 2) 허용 구간 밖부터는 "완만→급격" 감점 (제곱)
                double over = diff - tol; // 허용 구간을 얼마나 넘었는지
                // scale은 너가 민감도 조절하는 노브(값이 클수록 더 빨리 깎임)
                double scale = 120.0; // 시작값(너 운동 데이터 보고 80~200에서 튜닝)
                double penalty = scale * over * over;  // 제곱 벌점

                yield 100.0 - penalty;
            }

            // [감점형] 0(정지/안정)이 목표인 경우 (발목 흔들림 등)
            case "비마비측 발목 흔들림" -> {
                double error = Math.abs(measured); // RMS 값
                yield 100.0 - (error * getPenaltyWeight(name));
            }

            // [달성형] 목표치를 넘어야 하는 경우 (압력, 각도 등)
            case "어깨 외전 각도", "마비측 발판 압력" -> {
                if (finalTarget <= 0 || measured <= 0) yield 0.0;
                double rate = (measured / finalTarget) * 100;
                yield round1(rate);
            }

            // 그 외 기본 처리 (0 기준 감점)
            default -> {
                double error = Math.abs(measured);
                yield 100.0 - (error * getPenaltyWeight(name));
            }
        };

        // 2. 최종 점수 범위 제한 (0~100)
        return Math.max(0.0, Math.min(100.0, rawScore));
    }

    private double getFinalTargetValue(ExerciseGoal goal, Patient patient) {
        if ("마비측 발판 압력".equals(goal.getName())) {
            if (patient.getWeight() != null) {
                return patient.getWeight().doubleValue() * (goal.getTargetValue() / 100.0);
            }
            return 50.0; // 기본값
        }
        return goal.getTargetValue(); // 압력이 아니면 DB에 설정된 값(180 등) 반환
    }

    private double getPenaltyWeight(String name) {
        return switch (name) {
            case "골반 수평 편차", "어깨 수평 불균형" -> 10.0;
            case "상체 앞뒤 기울기" -> 20.0;
            case "수행 가속도" -> 20.0;
            case "비마비측 발목 흔들림" -> 2500.0;
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

    private String mapGoalNameToFailId(String goalName) {
        return switch (goalName) {
            case "어깨 외전 각도" -> "F_SH_FLEX";
            case "팔꿈치 신전 상태" -> "F_EL_EXT";
            case "상체 앞뒤 기울기" -> "F_TR_TILT";
            case "어깨 수평 불균형" -> "F_SH_HOR";
            case "수행 가속도" -> "F_ACCEL";
            case "마비측 발판 압력" -> "F_PR_LOAD";
            case "골반 수평 편차" -> "F_PL_HOR";
            case "비마비측 발목 흔들림" -> "F_ANK_STB";
            default -> "F_ELSE"; // 예외 케이스용 일반 실패 코드
        };
    }

    private static double round1(double v) {
        return Math.round(v * 10.0) / 10.0;
    }
}