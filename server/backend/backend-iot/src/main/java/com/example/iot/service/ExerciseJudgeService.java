package com.example.iot.service;

import com.example.iot.redis.LatestJointRedisReader;
import com.example.iot.redis.dto.JointLatestValue;
import org.springframework.stereotype.Service;

@Service
public class ExerciseJudgeService {

    private final LatestJointRedisReader redisReader;

    public ExerciseJudgeService(LatestJointRedisReader redisReader) {
        this.redisReader = redisReader;
    }

    public JudgeResult judgeShoulderFlexionPeak(String deviceId, String side) {
        // 예시: 필요한 관절들을 Redis에서 읽음
        JointLatestValue shoulder = redisReader.getLatest(deviceId, side + "_shoulder")
                .orElseThrow(() -> new IllegalStateException("No data: shoulder"));
        JointLatestValue wrist = redisReader.getLatest(deviceId, side + "_wrist")
                .orElseThrow(() -> new IllegalStateException("No data: wrist"));

        // 예시 판정: 손목이 어깨보다 충분히 위로 올라갔는지
        boolean ok = wrist.y() < shoulder.y() - 0.05; // 좌표계에 따라 부호는 바꿔야 함
        String reason = ok ? "OK" : "Wrist not high enough";

        return new JudgeResult(ok, reason, shoulder.ts());
    }

    public record JudgeResult(boolean ok, String reason, String ts) {}
}