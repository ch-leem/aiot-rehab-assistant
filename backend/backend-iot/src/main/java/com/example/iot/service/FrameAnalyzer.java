package com.example.iot.service;

import com.example.iot.dto.request.TryEvaluationRequest;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class FrameAnalyzer {

    private final ObjectMapper objectMapper;

    /**
     * @param rawFrame : 최신 프레임 JSON (latest)
     * @param agg      : Redis에서 가져온 집계 데이터 Map (sum, count, max 포함)
     * @param side     : 환자의 마비측 ("LEFT" or "RIGHT")
     */
    public TryEvaluationRequest analyzeSummary(String rawFrame, Map<Object, Object> agg, String side) {
        TryEvaluationRequest req = new TryEvaluationRequest();
        if (agg == null || agg.isEmpty()) {
            log.warn("분석할 Redis 집계 데이터(agg)가 비어있습니다.");
            return req;
        }

        String sidePrefix = side.equalsIgnoreCase("LEFT") ? "l_" : "r_";
        String nonSidePrefix = side.equalsIgnoreCase("LEFT") ? "r_" : "l_"; // 비마비측 (발목 흔들림용)

        // 1. Latest 데이터 처리 (필요시 사용)
        try {
            if (rawFrame != null && !rawFrame.isEmpty()) {
                JsonNode root = objectMapper.readTree(rawFrame);
                // 추가 로직 필요 시 작성
            }
        } catch (Exception e) {
            log.error("Latest JSON 파싱 실패: ", e);
        }

        // 2. Agg 데이터를 통한 지표 계산 (평균/최대 전환 유연성 확보)

        // [MAIN] 어깨 외전 각도: 최대값 사용
        req.setMaxShoulderFlexionAngle(getVal(agg, "max." + sidePrefix + "shoulder_flexion"));

        // [MAIN] 팔꿈치 신전 상태: 평균값 사용 (Sum / Count)
        req.setAvgElbowExtensionAngle(getAverage(agg,
                "sum." + sidePrefix + "elbow_extension",
                "count." + sidePrefix + "elbow_extension"));

        // [MAIN] 마비측 발판 압력: 최대값 사용 (Power = 압력)
        req.setMaxPressure(getVal(agg, "max.power"));

        // [SUB] 상체 앞뒤 기울기: 평균값 사용
        req.setAvgTrunkForwardTilt(getAverage(agg, "sum.trunk_forward_tilt", "count.trunk_forward_tilt"));

        // [SUB] 어깨 수평/골반 수평 불균형: 평균값 사용
        double avgLevelDiff = getAverage(agg, "sum.pelvis_level", "count.pelvis_level");
        req.setAvgShoulderLevelDiff(avgLevelDiff); // 어깨 수평 불균형 목표용
        req.setAvgPelvisLevelDiff(avgLevelDiff);   // 골반 수평 편차 목표용

        // [SUB] 수행 가속도: 평균값 사용 (Strength = 가속도)
        req.setAvgMovementAcceleration(getAverage(agg, "sum.strength", "count.strength"));

        // [SUB] 비마비측 발목 흔들림: XYZ 편차 거리 환산
        req.setAnkleSwayDistance(calculateAnkleSway(agg, nonSidePrefix));

        return req;
    }

    // --- Helper Methods ---

    private double getVal(Map<Object, Object> agg, String key) {
        Object val = agg.get(key);
        if (val == null) return 0.0;
        try {
            return Double.parseDouble(val.toString());
        } catch (NumberFormatException e) {
            log.error("Redis 데이터 형식 오류 - Key: {}, Value: {}", key, val);
            return 0.0;
        }
    }

    private double getAverage(Map<Object, Object> agg, String sumKey, String countKey) {
        double sum = getVal(agg, sumKey);
        double count = getVal(agg, countKey);
        return count > 0 ? sum / count : 0.0;
    }

    private double calculateAnkleSway(Map<Object, Object> agg, String sidePrefix) {
        double dx = getVal(agg, "max." + sidePrefix + "ankle_x") - getVal(agg, "min." + sidePrefix + "ankle_x");
        double dy = getVal(agg, "max." + sidePrefix + "ankle_y") - getVal(agg, "min." + sidePrefix + "ankle_y");
        double dz = getVal(agg, "max." + sidePrefix + "ankle_z") - getVal(agg, "min." + sidePrefix + "ankle_z");
        return Math.sqrt(Math.pow(dx, 2) + Math.pow(dy, 2) + Math.pow(dz, 2));
    }
}