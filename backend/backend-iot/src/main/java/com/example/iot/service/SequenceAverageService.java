package com.example.iot.service;

import com.example.iot.domain.Session;
import com.example.iot.repository.SessionRepository;
import jakarta.transaction.Transactional;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;

@Service
public class SequenceAverageService {

    private final SessionRepository sessionRepo;

    public SequenceAverageService(SessionRepository sessionRepo) {
        this.sessionRepo = sessionRepo;
    }

    /**
     * sequenceId에 속한 모든 Session의
     * (successTries / totalTries) 평균을 퍼센트(BigDecimal)로 계산
     *
     * 반환 예:
     *  - 0.00 ~ 100.00
     */
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
            int success = session.getSuccessTries();

            // total이 0이면 계산 불가 → 제외
            if (total <= 0) {
                continue;
            }

            BigDecimal successBd = BigDecimal.valueOf(success);
            BigDecimal totalBd = BigDecimal.valueOf(total);

            // 성공률 (0.0000 ~ 1.0000)
            BigDecimal rate = successBd.divide(
                    totalBd,
                    4,                  // 소수 4자리
                    RoundingMode.HALF_UP
            );

            sumRate = sumRate.add(rate);
            validSessionCount++;
        }

        if (validSessionCount == 0) {
            return BigDecimal.ZERO;
        }

        // 평균 성공률 → 퍼센트 변환
        return sumRate
                .divide(
                        BigDecimal.valueOf(validSessionCount),
                        4,
                        RoundingMode.HALF_UP
                )
                .multiply(BigDecimal.valueOf(100))   // %
                .setScale(2, RoundingMode.HALF_UP);  // 소수 2자리 퍼센트
    }
}