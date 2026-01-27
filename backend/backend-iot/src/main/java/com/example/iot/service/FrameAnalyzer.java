package com.example.iot.service;

import com.example.iot.dto.request.TryEvaluationRequest;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class FrameAnalyzer {

    private final ObjectMapper objectMapper;

    /**
     * Redis에서 이미 집계(Max, Avg 등)된 단일 JSON 문자열을 파싱하여 DTO로 반환합니다.
     */
    public TryEvaluationRequest analyzeSummary(String rawFrame, String side) {
        TryEvaluationRequest req = new TryEvaluationRequest();

        if (rawFrame == null || rawFrame.isEmpty()) {
            log.warn("분석할 Redis 데이터가 비어있습니다.");
            return req;
        }

        String sideKey = side.toLowerCase(); // "left" or "right"

        try {
            // Redis가 준 요약본 JSON을 트리 구조로 읽음
            JsonNode root = objectMapper.readTree(rawFrame);

            // 1. 각도 관련 통계 (Redis가 이미 max, avg를 계산해서 넣었다고 가정)
            // JSON 구조가 기존 프레임과 동일하다면 아래와 같이 접근하고,
            // 만약 평평한 구조(Flat JSON)라면 root.path("max_shoulder").asDouble() 식으로 수정 필요
            JsonNode deg = root.path("deg");

            req.setMaxShoulderFlexionAngle(deg.path(sideKey).path("shoulder_flexion").asDouble());
            req.setAvgElbowExtensionAngle(deg.path(sideKey).path("elbow_extension").asDouble());
            req.setMaxTrunkForwardTilt(deg.path("mid").path("trunk_forward_tilt").asDouble());

            // 2. 기타 통계 (가속도, 발목 흔들림 등 Redis 계산값)
            // Redis 집계 로직에 따라 경로를 유연하게 설정하세요.
            req.setAnkleSwayDistance(root.path("ankle_sway").asDouble(0.0));
            req.setMaxMovementAcceleration(root.path("max_accel").asDouble(0.0));

        } catch (Exception e) {
            log.error("JSON 요약 데이터 파싱 중 오류 발생: ", e);
        }

        return req;
    }
}