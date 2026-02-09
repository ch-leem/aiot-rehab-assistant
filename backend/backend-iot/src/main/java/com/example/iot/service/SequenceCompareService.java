package com.example.iot.service;

import com.example.iot.domain.Sequence;
import com.example.iot.domain.Session;
import com.example.iot.dto.response.GoalCompareItem;
import com.example.iot.dto.response.SequenceCompareResponse;
import com.example.iot.repository.SequenceRepository;
import com.example.iot.repository.SessionRepository;
import jakarta.transaction.Transactional;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.*;

@Service
public class SequenceCompareService {

    private final SequenceRepository sequenceRepository;
    private final SessionRepository sessionRepository;

    public SequenceCompareService(SequenceRepository sequenceRepository,
                                  SessionRepository sessionRepository) {
        this.sequenceRepository = sequenceRepository;
        this.sessionRepository = sessionRepository;
    }

    /**
     * 현재 시퀀스(currentSequenceId) 기준으로 "바로 이전 시퀀스 1개"를 찾아
     * 세션(goal)을 운동(exercise) 기준으로 매칭하여 diff(현재-이전)를 계산한다.
     */
    @Transactional
    public SequenceCompareResponse compareWithPrevious(Long patientId, Long currentSequenceId) {

        // 0) 현재 시퀀스 존재 + 환자 소유 검증
        Sequence current = sequenceRepository.findById(currentSequenceId)
                .orElseThrow(() -> new IllegalArgumentException("Current sequence not found: " + currentSequenceId));

        // Sequence가 patient를 엔티티로 들고 있을 때
        if (current.getPatient() == null || current.getPatient().getId() == null
                || !Objects.equals(current.getPatient().getId(), patientId)) {
            throw new IllegalArgumentException("Sequence does not belong to patient. patientId=" + patientId
                    + ", currentSequenceId=" + currentSequenceId);
        }

        // 1) 이전 시퀀스 찾기 (id 기준: currentSequenceId 보다 작은 것 중 최신 1개)
        Sequence prev = sequenceRepository.findPreviousByPatientAndCurrentId(patientId, currentSequenceId, PageRequest.of(0, 1))
                .stream().findFirst()
                .orElse(null);

        // 이전 시퀀스가 없으면 비교 불가 → 이전 없음으로 반환(또는 예외로 막아도 됨)
        if (prev == null) {
            return new SequenceCompareResponse(
                    patientId,
                    currentSequenceId,
                    null,
                    Collections.emptyList()
            );
        }

        // 2) 세션 가져오기 (운동까지 같이 필요하므로 fetch join 버전 추천)
        // 아래 메서드 이름은 레포지토리에 맞춰 구현해야 함.
        List<Session> currentSessions = sessionRepository.findBySequenceIdWithExercise(currentSequenceId);
        List<Session> prevSessions = sessionRepository.findBySequenceIdWithExercise(prev.getId());

        // 3) 이전 세션을 운동ID 기준으로 매핑
        Map<Long, Session> prevByExerciseId = new HashMap<>();
        for (Session s : prevSessions) {
            if (s.getExercise() != null && s.getExercise().getId() != null) {
                prevByExerciseId.put(s.getExercise().getId(), s);
            }
        }

        // 4) 현재 세션을 돌면서 (현재 - 이전) goal diff 계산
        List<GoalCompareItem> items = new ArrayList<>();
        for (Session curS : currentSessions) {
            Long exerciseId = (curS.getExercise() == null) ? null : curS.getExercise().getId();
            String exerciseName = (curS.getExercise() == null) ? "" : nullSafe(curS.getExercise().getName());

            String currentGoal = normalizeNumberString(curS.getGoal());
            String previousGoal = null;

            if (exerciseId != null && prevByExerciseId.containsKey(exerciseId)) {
                previousGoal = normalizeNumberString(prevByExerciseId.get(exerciseId).getGoal());
            }

            String diff = null;
            if (previousGoal != null && isParsableNumber(previousGoal) && isParsableNumber(currentGoal)) {
                BigDecimal d = new BigDecimal(currentGoal).subtract(new BigDecimal(previousGoal));
                diff = d.stripTrailingZeros().toPlainString();
            }

            items.add(new GoalCompareItem(
                    exerciseId,
                    exerciseName,
                    previousGoal,     // 이전 기록 없으면 null
                    currentGoal,
                    diff              // 숫자면 diff, 아니면 null
            ));
        }

        return new SequenceCompareResponse(
                patientId,
                currentSequenceId,
                prev.getId(),
                items
        );
    }

    private static String nullSafe(String s) {
        return s == null ? "" : s;
    }

    /**
     * goal이 String일 때 숫자 비교를 위해 정규화
     * - null/blank -> "0"
     * - "82.5%" 같은 경우 % 제거
     */
    private static String normalizeNumberString(String s) {
        if (s == null) return "0";
        String t = s.trim();
        if (t.isEmpty()) return "0";
        // 퍼센트 같은 문자 제거(원하면 더 확장 가능)
        t = t.replace("%", "");
        return t;
    }

    private static boolean isParsableNumber(String s) {
        try {
            new BigDecimal(s.trim());
            return true;
        } catch (Exception e) {
            return false;
        }
    }
}