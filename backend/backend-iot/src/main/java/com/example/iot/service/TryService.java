package com.example.iot.service;

import com.example.iot.domain.*;
import com.example.iot.domain.constant.TryResult;
import com.example.iot.dto.request.TryEvaluationRequest;
import com.example.iot.dto.response.TryFinishResponse;
import com.example.iot.dto.response.TryStartResponse;
import com.example.iot.repository.*;
import lombok.Getter;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;

@Slf4j
@Service
@RequiredArgsConstructor
public class TryService {

    private static final double SUCCESS_THRESHOLD_PERCENT = 70.0;

    private final TryRepository tryRepository;
    private final FailRepository failRepository;
    private final ExerciseGoalRepository exerciseGoalRepository;
    private final ExercisePatientMappingRepository mappingRepository;
    private final FrameAnalyzer frameAnalyzer;

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

        Session session = t.getSession();
        Exercise exercise = session.getExercise();
        Patient patient = session.getSequence().getPatient();

        ExercisePatientMapping mapping = mappingRepository.findByPatient_Id(patient.getId()).stream()
                .filter(m -> m.getExercise().getId().equals(exercise.getId()))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Mapping 정보가 없습니다."));

        String side = mapping.getSide().name();
        TryEvaluationRequest evalRequest = frameAnalyzer.analyzeSummary(rawFrame, agg, side);
        List<ExerciseGoal> goals = exerciseGoalRepository.findByExercise(exercise);

        TryGoalResult mainResult = null;
        TryGoalResult accelResult = null;
        List<TryGoalResult> otherSubResults = new ArrayList<>();
        Map<String, Integer> branchScores = new HashMap<>();

        // 1. 모든 지표 점수 계산 및 수집
        List<TryGoalResult> allResults = new ArrayList<>(); // 전체 평균 계산용
        for (ExerciseGoal goal : goals) {
            String name = goal.getName();
            double measuredValue = evalRequest.getValueByGoalName(name);
            double finalTarget = getFinalTargetValue(goal, patient);

            // [A] DB용 정밀 점수
            double achievementRate = calculateAchievement(goal, measuredValue, finalTarget);
            TryGoalResult result = new TryGoalResult(t, goal, measuredValue, achievementRate);
            t.addGoalResult(result);
            allResults.add(result);

            // [B] 프론트 판정용 분기 점수 (ErrorComponent 활용)
            int branchScore = ErrorComponent.errorScoreFromAbsErrorAgg(
                    finalTarget,
                    goal.getThreshold(),
                    evalRequest.getCountByGoalName(name),
                    evalRequest.getSumByGoalName(name),
                    "비마비측 발목 흔들림".equals(name)
            );
            branchScores.put(name, branchScore);

            // 분류 (우선순위 판정을 위함)
            if ("MAIN".equals(goal.getGoalType())) {
                mainResult = result;
            } else if ("수행 가속도".equals(name)) {
                accelResult = result;
            } else {
                otherSubResults.add(result);
            }
        }

        t.setEndedAt(LocalDateTime.now());

        // 전체 평균 계산 (MAIN, 가속도, SUB 모두 포함) - 성공/실패 여부와 관계없음
        double totalAverage = allResults.stream()
                .mapToDouble(TryGoalResult::getAchievementRate)
                .average()
                .orElse(0.0);

        // 2. 내부 DB 결과 판정 (정밀 점수 기준)
        JudgeResult dbJudge = determineJudge(mainResult, accelResult, otherSubResults, null, totalAverage);
        if (dbJudge.isFailed()) {
            setTryFailure(t, dbJudge.getFailGoalName());
        } else {
            t.setResult(TryResult.SUCCESS);
            if (session != null) session.setSuccessTries(session.getSuccessTries() + 1);
        }
        t.setTotalScore(totalAverage); // DB에는 계산된 전체 평균 저장

        // 3. 프론트엔드 응답 판정 (분기 점수 기준)
        JudgeResult frontJudge = determineJudge(mainResult, accelResult, otherSubResults, branchScores, totalAverage);

        // 4. 최종 응답 생성 (DB 결과와 독립적으로 frontJudge 사용)
        return toResponse(t,
                frontJudge.isFailed() ? "FAIL" : "SUCCESS",
                frontJudge.getFailGoalName(),
                frontJudge.isFailed() ? mapGoalNameToFailId(frontJudge.getFailGoalName()) : null);
    }

    /**
     * 공통 판정 로직: MAIN -> 가속도 -> SUB 순서
     * scoresMap이 null이면 DB용(70점), 존재하면 프론트용(100점) 기준으로 작동
     */
    private JudgeResult determineJudge(TryGoalResult main, TryGoalResult accel, List<TryGoalResult> subs, Map<String, Integer> scoresMap, double calculatedTotal) {
        // 1. MAIN 우선 판정
        if (main != null && isFailedItem(main, scoresMap)) {
            return new JudgeResult(true, main.getExerciseGoal().getName(), calculatedTotal);
        }
        // 2. 가속도 우선 판정
        if (accel != null && isFailedItem(accel, scoresMap)) {
            return new JudgeResult(true, accel.getExerciseGoal().getName(), calculatedTotal);
        }
        // 3. SUB 판정 및 최저점 탐색
        TryGoalResult worstSub = subs.stream()
                .filter(s -> isFailedItem(s, scoresMap))
                .min(Comparator.comparingDouble(s -> getScoreValue(s, scoresMap)))
                .orElse(null);

        if (worstSub != null) {
            return new JudgeResult(true, worstSub.getExerciseGoal().getName(), calculatedTotal);
        }

        // 실패가 없으면 성공
        return new JudgeResult(false, null, calculatedTotal);
    }

    private boolean isFailedItem(TryGoalResult item, Map<String, Integer> scoresMap) {
        if (scoresMap == null) return item.getAchievementRate() < SUCCESS_THRESHOLD_PERCENT;
        return scoresMap.get(item.getExerciseGoal().getName()) < 100;
    }

    private double getScoreValue(TryGoalResult item, Map<String, Integer> scoresMap) {
        if (scoresMap == null) return item.getAchievementRate();
        return scoresMap.get(item.getExerciseGoal().getName());
    }

    private void setTryFailure(Try t, String failGoalName) {
        t.setResult(TryResult.FAIL);
        String failId = mapGoalNameToFailId(failGoalName);
        failRepository.findById(failId).ifPresent(t::setFail);
    }

    private double calculateAchievement(ExerciseGoal goal, double measured, double finalTarget) {
        String name = goal.getName();
        double rawScore = switch (name) {
            case "상체 앞뒤 기울기" -> {
                double error = Math.abs(finalTarget - measured);
                yield (error <= 5) ? 100.0 - (error * 5) : Math.max(60.0, 100.0 - (Math.pow(error, 2) * getPenaltyWeight(name)));
            }
            case "어깨 수평 불균형", "골반 수평 편차", "팔꿈치 신전 상태", "비마비측 발목 흔들림" ->
                    100.0 - (Math.abs(finalTarget - measured) * getPenaltyWeight(name));
            case "수행 가속도" -> {
                double diff = Math.abs((measured / finalTarget) - 1.0);
                yield (diff <= 0.10) ? 100.0 : 100.0 - (120.0 * Math.pow(diff - 0.10, 2));
            }
            case "어깨 외전 각도", "마비측 발판 압력" -> (finalTarget <= 0) ? 0.0 : (measured / finalTarget) * 100;
            default -> 100.0 - Math.abs(finalTarget - measured);
        };
        return Math.max(0.0, Math.min(100.0, rawScore));
    }

    private double getFinalTargetValue(ExerciseGoal goal, Patient patient) {
        if ("마비측 발판 압력".equals(goal.getName()) && patient.getWeight() != null) {
            return patient.getWeight().doubleValue() * (goal.getTargetValue() / 100.0);
        }
        return goal.getTargetValue();
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

    private TryFinishResponse toResponse(Try t, String status, String failName, String failId) {
        return new TryFinishResponse(t.getId(), t.getTotalScore(), status, failName, failId);
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

    // 내부 판정 결과 캡슐화 객체
    @Getter
    @RequiredArgsConstructor
    private static class JudgeResult {
        private final boolean failed;
        private final String failGoalName;
        private final double totalScore;
    }
}