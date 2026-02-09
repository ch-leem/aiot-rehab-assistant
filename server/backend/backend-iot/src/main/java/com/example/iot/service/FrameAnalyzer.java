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
        String nonSidePrefix = side.equalsIgnoreCase("LEFT") ? "r_" : "l_"; // 비마비측

        // 1. Latest 데이터 처리 (필요시 사용)
        try {
            if (rawFrame != null && !rawFrame.isEmpty()) {
                JsonNode root = objectMapper.readTree(rawFrame);
            }
        } catch (Exception e) {
            log.error("Latest JSON 파싱 실패: ", e);
        }

        // 2. Agg 데이터를 통한 지표 계산 및 원천 데이터(sum, count) 보관

        // [MAIN] 어깨 외전 각도 (Max)
        String shKey = sidePrefix + "shoulder_flexion";
        req.setMaxShoulderFlexionAngle(getVal(agg, "max." + shKey));
        req.addStats("어깨 외전 각도", getVal(agg, "sum." + shKey), getCount(agg, "count." + shKey));

        // [MAIN] 마비측 발판 압력 (Max)
        req.setMaxPressure(getVal(agg, "max.power"));
        req.addStats("마비측 발판 압력", getVal(agg, "sum.power"), getCount(agg, "count.power"));

        // [SUB] 팔꿈치 신전 상태 (Avg)
        String elKey = sidePrefix + "elbow_extension";
        req.setAvgElbowExtensionAngle(getAverage(agg, "sum." + elKey, "count." + elKey));
        req.addStats("팔꿈치 신전 상태", getVal(agg, "sum." + elKey), getCount(agg, "count." + elKey));

        // [SUB] 상체 앞뒤 기울기 (Avg)
        req.setAvgTrunkForwardTilt(getAverage(agg, "sum.trunk_forward_tilt", "count.trunk_forward_tilt"));
        req.addStats("상체 앞뒤 기울기", getVal(agg, "sum.trunk_forward_tilt"), getCount(agg, "count.trunk_forward_tilt"));

        // [SUB] 어깨 수평 불균형 (Avg)
        String shRotKey = "trunk_rotation_lateral_flexion";
        req.setAvgShoulderLevelDiff(getAverage(agg, "sum." + shRotKey, "count." + shRotKey));
        req.addStats("어깨 수평 불균형", getVal(agg, "sum." + shRotKey), getCount(agg, "count." + shRotKey));

        // [SUB] 골반 수평 편차 (Avg)
        String pelKey = "pelvis_level";
        req.setAvgPelvisLevelDiff(getAverage(agg, "sum." + pelKey, "count." + pelKey));
        req.addStats("골반 수평 편차", getVal(agg, "sum." + pelKey), getCount(agg, "count." + pelKey));

        // [SUB] 수행 가속도 (Avg)
        String accKey = "strength";
        req.setAvgMovementAcceleration(getAverage(agg, "sum." + accKey, "count." + accKey)); // DB 저장/점수용
        req.setMaxMovementAcceleration(getVal(agg, "max." + accKey)); // [추가] 순수 판정용 (100 체크)
        req.addStats("수행 가속도", getVal(agg, "sum." + accKey), getCount(agg, "count." + accKey));

        // [SUB] 비마비측 발목 흔들림 (Ankle Sway)
        // 흔들림의 경우 ErrorComponent에서 사용할 sumE 계산을 위해 원천 count와 sum_sq를 매핑
        String swayKey = nonSidePrefix + "ankle_jitter";
        req.setAnkleSwayDistance(calculateAnkleSway(agg, swayKey));
        req.addStats("비마비측 발목 흔들림", getVal(agg, "sum_sq." + swayKey), getCount(agg, "count." + swayKey));

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

    private long getCount(Map<Object, Object> agg, String key) {
        return (long) getVal(agg, key);
    }

    private double getAverage(Map<Object, Object> agg, String sumKey, String countKey) {
        double sum = getVal(agg, sumKey);
        double count = getVal(agg, countKey);
        return count > 0 ? sum / count : 0.0;
    }

    // RMS로 계산
    private double calculateAnkleSway(Map<Object, Object> agg, String baseKey) {
        double sumSq = getVal(agg, "sum_sq." + baseKey);
        double count = getVal(agg, "count." + baseKey);
        if (count <= 0) return 0.0;
        return Math.sqrt(sumSq / count);
    }
}