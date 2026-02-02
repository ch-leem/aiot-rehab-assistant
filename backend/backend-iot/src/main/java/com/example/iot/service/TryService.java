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

        TryGoalResult mainResult = null;
        TryGoalResult accelResult = null;
        java.util.List<TryGoalResult> otherSubResults = new java.util.ArrayList<>();

        for (ExerciseGoal goal : goals) {
            double measuredValue = evalRequest.getValueByGoalName(goal.getName());
            double finalTarget = getFinalTargetValue(goal, patient);
            double achievementRate = calculateAchievement(goal, measuredValue, finalTarget);

            TryGoalResult result = new TryGoalResult(t, goal, measuredValue, achievementRate);
            t.addGoalResult(result); // DB 저장을 위해 리스트에 추가

            // 판정을 위한 분류
            if ("MAIN".equals(goal.getGoalType())) {
                mainResult = result;
            } else if ("수행 가속도".equals(goal.getName())) {
                accelResult = result;
            } else {
                otherSubResults.add(result);
            }
        }

        t.setEndedAt(LocalDateTime.now());

        // 4. 순차적 성공/실패 판정 (Step-by-Step Gate)
        boolean isFailed = false;

        // [관문 1] MAIN 목표 확인
        if (mainResult != null && mainResult.getAchievementRate() < SUCCESS_THRESHOLD_PERCENT) {
            setTryFailure(t, mainResult.getExerciseGoal().getName());
            isFailed = true;
        }

        // [관문 2] 가속도 항목 확인 (MAIN 통과 시에만)
        if (!isFailed && accelResult != null && accelResult.getAchievementRate() < SUCCESS_THRESHOLD_PERCENT) {
            setTryFailure(t, accelResult.getExerciseGoal().getName());
            isFailed = true;
        }

        // [관문 3] 나머지 SUB 목표 평균 확인 (앞선 관문 통과 시에만)
        if (!isFailed) {
            double otherSubAvg = otherSubResults.stream()
                    .mapToDouble(TryGoalResult::getAchievementRate)
                    .average()
                    .orElse(100.0);

            t.setTotalScore(otherSubAvg); // 최종 점수로 활용

            if (otherSubAvg < SUCCESS_THRESHOLD_PERCENT) {
                // 평균 미달 시 그 중 최저 점수인 항목을 실패 사유로 제출
                String worstSubName = otherSubResults.stream()
                        .min(java.util.Comparator.comparing(TryGoalResult::getAchievementRate))
                        .map(r -> r.getExerciseGoal().getName())
                        .orElse("기타");
                setTryFailure(t, worstSubName);
            } else {
                // 모든 관문 통과
                t.setResult(TryResult.SUCCESS);
                session.setSuccessTries(session.getSuccessTries() + 1);
            }
        }

        return toResponse(t);
    }

    private void setTryFailure(Try t, String failGoalName) {
        t.setResult(TryResult.FAIL);
        String failId = mapGoalNameToFailId(failGoalName);
        Fail fail = failRepository.findById(failId).orElse(null);
        t.setFail(fail);
    }

    /**
     * 개별 목표 달성률 계산
     */
    private double calculateAchievement(ExerciseGoal goal, double measured, double finalTarget) {
        String name = goal.getName();
        double rawScore;

        // DB에서 넘어온 finalTarget(목표값)을 기준으로 계산합니다.
        rawScore = switch (name) {

            case "상체 앞뒤 기울기" -> {
                double error = Math.abs(finalTarget - measured);
                double score;
                if (error <= 5) {
                    score = 100.0 - (error * 5);
                } else {
                    double penalty = Math.pow(error, 2) * getPenaltyWeight(name);
                    score = 100.0 - penalty;
                }
                yield Math.max(60.0, score);
            }

            case "어깨 수평 불균형", "골반 수평 편차", "팔꿈치 신전 상태" -> {
                double error = Math.abs(finalTarget - measured);
                yield 100.0 - (error * getPenaltyWeight(name));
            }


            case "수행 가속도" -> {
                double ratio = measured / finalTarget; // DB의 targetValue가 기준 속도가 됨
                double tol = 0.10;
                double diff = Math.abs(ratio - 1.0);

                if (diff <= tol) yield 100.0;
                double over = diff - tol;
                yield 100.0 - (120.0 * over * over);
            }

            case "비마비측 발목 흔들림" -> {
                // 흔들림은 0에 가까울수록 좋으므로 targetValue가 보통 0입니다.
                double error = Math.abs(finalTarget - measured);
                yield 100.0 - (error * getPenaltyWeight(name));
            }

            case "어깨 외전 각도", "마비측 발판 압력" -> {
                if (finalTarget <= 0 || measured <= 0) yield 0.0;
                double rate = (measured / finalTarget) * 100;
                yield round1(rate);
            }

            default -> {
                double error = Math.abs(finalTarget - measured);
                yield 100.0 - (error * getPenaltyWeight(name));
            }
        };

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
                t.getFail() != null ? t.getFail().getName() : null,
                t.getFail() != null ? t.getFail().getId() : null
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