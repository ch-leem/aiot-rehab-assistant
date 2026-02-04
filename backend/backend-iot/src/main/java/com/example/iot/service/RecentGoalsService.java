package com.example.iot.service;

import com.example.iot.domain.Exercise;
import com.example.iot.domain.Sequence;
import com.example.iot.domain.Session;
import com.example.iot.dto.response.ExerciseRecentGoalsItem;
import com.example.iot.dto.response.RecentGoalsByExerciseResponse;
import com.example.iot.repository.SequenceRepository;
import com.example.iot.repository.SessionRepository;
import jakarta.transaction.Transactional;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
public class RecentGoalsService {

    // 운동별 5개를 채우려면 시퀀스를 5개만 보면 부족할 수 있어서 넉넉히 뒤짐
    private static final int LOOKBACK_SEQUENCES = 50;
    private static final int RECENT_GOALS_PER_EXERCISE = 5;

    private final SequenceRepository sequenceRepository;
    private final SessionRepository sessionRepository;
    private final ExerciseService exerciseService;

    public RecentGoalsService(SequenceRepository sequenceRepository,
                              SessionRepository sessionRepository,
                              ExerciseService exerciseService) {
        this.sequenceRepository = sequenceRepository;
        this.sessionRepository = sessionRepository;
        this.exerciseService = exerciseService;
    }

    @Transactional
    public RecentGoalsByExerciseResponse getRecent5GoalsByExercise(Long patientId, Long currentSequenceId) {

        // 1) 오늘(currentSequenceId) 제외하고 이전 시퀀스들 가져오기
        List<Sequence> prevSeqs = sequenceRepository.findPreviousSequences(
                patientId,
                currentSequenceId,
                PageRequest.of(0, LOOKBACK_SEQUENCES)
        );

        if (prevSeqs.isEmpty()) {
            return new RecentGoalsByExerciseResponse(
                    patientId,
                    currentSequenceId,
                    0,
                    Collections.emptyList()
            );
        }

        // 최신순(큰 id -> 작은 id)
        List<Long> seqIdsDesc = prevSeqs.stream()
                .map(Sequence::getId)
                .collect(Collectors.toList());

        // 2) 해당 시퀀스들의 session(운동,goal) 가져오기
        List<Session> sessions = sessionRepository.findBySequenceIdsWithExercise(seqIdsDesc);

        // 3) sequenceId 최신순으로 정렬(혹시 DB가 IN에서 순서를 보장 안 할 수 있으니)
        sessions.sort((a, b) -> Long.compare(b.getSequence().getId(), a.getSequence().getId()));

        // 4) exerciseId별로 goal을 최근순으로 최대 5개씩 모으기
        //    LinkedHashMap 사용하면 들어간 순서(최근순)를 유지하기 좋음
        Map<Long, ExerciseBucket> bucketMap = new LinkedHashMap<>();

        for (Session s : sessions) {
            Long exId = s.getExercise().getId();
            Exercise exercise = exerciseService.getExercise(exId);
            String exName = (exercise != null) ? exercise.getName() : "Unknown";
            int success = s.getSuccessTries();
            int total = s.getTotalTries();

            String goal = "";
            if(total == 0) {
                goal = "0";
            } else{
                double temp = (double) ((double)success / (double)total) * 100;
                log.info("temp={}", temp);
                goal = String.valueOf(temp);
            }

            ExerciseBucket bucket = bucketMap.computeIfAbsent(exId, k -> new ExerciseBucket(exId, exName));

            if (bucket.goals.size() < RECENT_GOALS_PER_EXERCISE) {
                log.info("sucess = {}, total={}", success, total);
                bucket.goals.add(goal);
                log.info("sessionid={}", s.getId());
            }
        }

        List<ExerciseRecentGoalsItem> items = bucketMap.values().stream()
                .map(b -> new ExerciseRecentGoalsItem(b.exerciseId, b.exerciseName, b.goals))
                .toList();

        return new RecentGoalsByExerciseResponse(
                patientId,
                currentSequenceId,
                prevSeqs.size(),
                items
        );
    }

    private static String normalizeGoal(String g) {
        if (g == null) return "0";
        String t = g.trim();
        if (t.isEmpty()) return "0";
        return t.replace("%", "");
    }
    private static String percent(int success, int total) {
        if (total <= 0) return "0.0";
        return BigDecimal.valueOf(success)
                .multiply(BigDecimal.valueOf(100))
                .divide(BigDecimal.valueOf(total), 1, RoundingMode.HALF_UP)
                .toPlainString();
    }

    private static class ExerciseBucket {
        Long exerciseId;
        String exerciseName;
        List<String> goals = new ArrayList<>();

        ExerciseBucket(Long exerciseId, String exerciseName) {
            this.exerciseId = exerciseId;
            this.exerciseName = exerciseName == null ? "" : exerciseName;
        }
    }
}