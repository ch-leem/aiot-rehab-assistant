package com.example.iot.service;

import com.example.iot.domain.Session;
import com.example.iot.dto.response.SessionTryCountResponse;
import com.example.iot.repository.SessionRepository;
import jakarta.transaction.Transactional;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;
@Service
public class SequenceAverageService {

    private final SessionRepository sessionRepo;

    public SequenceAverageService(SessionRepository sessionRepo) {
        this.sessionRepo = sessionRepo;
    }

    @Transactional
    public BigDecimal calculateAverageSuccessPercent(Long sequenceId) {
        List<Session> sessions = sessionRepo.findBySequence_IdOrderByStartedAtAsc(sequenceId);

        if (sessions.isEmpty()) {
            return BigDecimal.ZERO;
        }

        BigDecimal sumRate = BigDecimal.ZERO;
        int validSessionCount = 0;

        for (Session session : sessions) {
            int total = session.getTotalTries();
            // int success = session.getSuccessTries();
            int success = Integer.parseInt(session.getGoal());

            if (total <= 0) continue;

            BigDecimal rate = BigDecimal.valueOf(success)
                    .divide(BigDecimal.valueOf(total), 4, RoundingMode.HALF_UP);

            sumRate = sumRate.add(rate);
            validSessionCount++;
        }

        if (validSessionCount == 0) {
            return BigDecimal.ZERO;
        }

        return sumRate
                .divide(BigDecimal.valueOf(validSessionCount), 4, RoundingMode.HALF_UP)
                .multiply(BigDecimal.valueOf(100))
                .setScale(2, RoundingMode.HALF_UP);
    }

    /**
     */
    @Transactional
    public List<SessionTryCountResponse> getSessionTryCounts(Long sequenceId) {
        List<Session> sessions = sessionRepo.findBySequence_IdOrderByStartedAtAsc(sequenceId);

        List<SessionTryCountResponse> result = new ArrayList<>();

        for (Session s : sessions) {
            int total = Math.max(0, s.getTotalTries());
            // int success = Math.max(0, s.getSuccessTries());
             int success = Math.max(0, Integer.parseInt(normalizeGoal(s.getGoal())));

            // 실패 횟수는 total - success 로 계산 (음수 방지)
            // int fail = Math.max(0, total - success);
            Long exerciseId = s.getExercise().getId();

            // (선택) 세션별 성공률 %
            BigDecimal percent = BigDecimal.ZERO;
            if (total > 0) {
                percent = BigDecimal.valueOf(success)
                        .divide(BigDecimal.valueOf(total), 4, RoundingMode.HALF_UP)
                        .multiply(BigDecimal.valueOf(100))
                        .setScale(2, RoundingMode.HALF_UP);
            }

            result.add(new SessionTryCountResponse(
                    exerciseId,   // Session 엔티티의 PK getter 이름이 getId()가 맞는지 확인 필요
                    total,
                    success
            ));
        }

        return result;
    }

    private static String normalizeGoal(String g) {
        if (g == null) return "0";
        String t = g.trim();
        if (t.isEmpty()) return "0";
        return t.replace("%", "");
    }
}