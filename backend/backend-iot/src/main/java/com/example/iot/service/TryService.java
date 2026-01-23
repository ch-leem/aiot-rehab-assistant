package com.example.iot.service;

import com.example.iot.domain.Fail;
import com.example.iot.domain.Session;
import com.example.iot.domain.Try;
import com.example.iot.domain.constant.TryResult;
import com.example.iot.dto.response.TryFinishResponse;
import com.example.iot.repository.FailRepository;
import com.example.iot.repository.SessionRepository;
import com.example.iot.repository.TryRepository;
import jakarta.transaction.Transactional;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.LocalDateTime;
import java.util.concurrent.ThreadLocalRandom;

@Service
public class TryService {

    private static final double SUCCESS_THRESHOLD_PERCENT = 80.0;

    private final TryRepository tryRepository;
    private final SessionRepository sessionRepository;
    private final FailRepository failRepository;

    public TryService(TryRepository tryRepository,
                      SessionRepository sessionRepository,
                      FailRepository failRepository) {
        this.tryRepository = tryRepository;
        this.sessionRepository = sessionRepository;
        this.failRepository = failRepository;
    }

    @Transactional
    public TryFinishResponse finishTry(Long tryId) {
        Try t = tryRepository.findById(tryId)
                .orElseThrow(() -> new IllegalArgumentException("Try not found: " + tryId));

        // 이미 끝난 try면 중복 처리 방지(선택)
        if (t.getEndedAt() != null) {
            // 이미 종료된 값 그대로 반환해도 되고, 에러로 막아도 됨
            return toResponse(t, "이미 종료되었습니다.");
        }

        // ======= (나중에 Redis 연동 들어갈 자리) =======
        // 1) Redis에서 sensor/vision 값 가져오기
        // 2) 로직 돌려 정확도(%) 계산
        // 3) 80% 이상 성공 / 미만 실패 + failType 계산
        //
        // 지금은 임시로 "랜덤 정확도"로 처리
        double accuracyPercent = ThreadLocalRandom.current().nextDouble(0, 100);
        boolean success = accuracyPercent >= SUCCESS_THRESHOLD_PERCENT;

        // goal 값도 당장은 임시로(나중에 Redis/로직 결과로 대체)
        double goalSensor = round1(accuracyPercent);                 // 예시
        double goalVision = round1(ThreadLocalRandom.current().nextDouble(0, 100)); // 예시
        // ===============================================

        // goal 값 기록(필드가 String이면 String으로, Double이면 Double로 맞춰)
        t.setGoalSensor(String.valueOf(goalSensor));
        t.setGoalVision(String.valueOf(goalVision));
        t.setEndedAt(LocalDateTime.now());

        Instant endedAt = Instant.now();
        //t.setEndedAt(endedAt);

        if (success) {
            // Try 성공 처리
            t.setResult(TryResult.SUCCESS);
            t.setFail(null);

            Session s = t.getSession();
            if (s != null) {
                s.setSuccessTries(s.getSuccessTries() + 1);
                sessionRepository.save(s);
            }

        } else {
            // Try 실패 처리
            t.setResult(TryResult.FAIL);
            Fail fail = failRepository.findById("1").orElse(null);
            t.setFail(fail);
        }



        String str = "";

        if(goalSensor >= 80 && goalVision >= 70) {
            str = "잘하고 계십니다!";
        } else if( goalSensor < 80) {
            str = "좀 더 힘을 눌러보세요.";
        } else {
            str = "움직임을 더 정확하게 해보세요.";
        }

        tryRepository.save(t);

        return new TryFinishResponse(
                t.getId(),
                str
//                (t.getFail() == null ? "" : t.getFail().getName()), // failType
//                t.getGoalSensor(),
//                t.getGoalVision()
//                t.getEndedAt()
        );
    }

    private TryFinishResponse toResponse(Try t, String str) {
        return new TryFinishResponse(
                t.getId(),
                str
//                (t.getFail() == null ? "" : t.getFail().getName()),
//                t.getGoalSensor(),
//                t.getGoalVision()
//                t.getEndedAt()
        );
    }

    private static double round1(double v) {
        return Math.round(v * 10.0) / 10.0;
    }
}