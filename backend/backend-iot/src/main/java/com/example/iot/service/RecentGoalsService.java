package com.example.iot.service;

import com.example.iot.domain.Sequence;
import com.example.iot.domain.Session;
import com.example.iot.dto.response.ExerciseRecentGoalsItem;
import com.example.iot.dto.response.RecentGoalsByExerciseResponse;
import com.example.iot.repository.SequenceRepository;
import com.example.iot.repository.SessionRepository;
import jakarta.transaction.Transactional;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.stream.Collectors;

@Service
public class RecentGoalsService {

    // 운동별 5개를 채우려면 시퀀스를 5개만 보면 부족할 수 있어서 넉넉히 뒤짐
    private static final int LOOKBACK_SEQUENCES = 50;
    private static final int RECENT_GOALS_PER_EXERCISE = 5;

    private final SequenceRepository sequenceRepository;
    private final SessionRepository sessionRepository;

    public RecentGoalsService(SequenceRepository sequenceRepository,
                              SessionRepository sessionRepository) {
        this.sequenceRepository = sequenceRepository;
        this.sessionRepository = sessionRepository;
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
            String exName = s.getExercise().getName();
            String goal = normalizeGoal(s.getGoal());

            ExerciseBucket bucket = bucketMap.computeIfAbsent(exId, k -> new ExerciseBucket(exId, exName));

            if (bucket.goals.size() < RECENT_GOALS_PER_EXERCISE) {
                bucket.goals.add(goal);
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