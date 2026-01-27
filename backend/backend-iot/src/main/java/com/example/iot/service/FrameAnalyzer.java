package com.example.iot.service;

import com.example.iot.dto.request.TryEvaluationRequest;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class FrameAnalyzer {

    private final ObjectMapper objectMapper;

    /**
     * raw JSON 리스트를 분석하여 통계 수치(DTO)를 반환합니다.
     * redis에서 받아온 string 데이터를 json으로 파싱했다고 가정
     */
    public TryEvaluationRequest analyze(List<String> rawFrames, String side) {
        if (rawFrames == null || rawFrames.isEmpty()) {
            return new TryEvaluationRequest();
        }

        List<Double> shoulderAngles = new ArrayList<>();
        List<Double> elbowAngles = new ArrayList<>();
        List<Double> trunkTilts = new ArrayList<>();
        List<Double> ankleX = new ArrayList<>(), ankleY = new ArrayList<>(), ankleZ = new ArrayList<>();

        String sideKey = side.toLowerCase(); // "left" or "right"

        try {
            for (String json : rawFrames) {
                JsonNode root = objectMapper.readTree(json);
                JsonNode deg = root.path("deg");
                JsonNode pos = root.path("position");

                // 각도 추출
                shoulderAngles.add(deg.path(sideKey).path("shoulder_flexion").asDouble());
                elbowAngles.add(deg.path(sideKey).path("elbow_extension").asDouble());
                trunkTilts.add(deg.path("mid").path("trunk_forward_tilt").asDouble());

                // 발목 흔들림 좌표 추출
                JsonNode ankle = pos.path(sideKey).path(sideKey + "_ankle");
                ankleX.add(ankle.path("x").asDouble());
                ankleY.add(ankle.path("y").asDouble());
                ankleZ.add(ankle.path("z").asDouble());
            }
        } catch (Exception e) {
            log.error("JSON 파싱 중 오류 발생: ", e);
        }

        TryEvaluationRequest req = new TryEvaluationRequest();
        if (!shoulderAngles.isEmpty()) {
            req.setMaxShoulderFlexionAngle(Collections.max(shoulderAngles));
            req.setAvgElbowExtensionAngle(elbowAngles.stream().mapToDouble(d -> d).average().orElse(0.0));
            req.setMaxTrunkForwardTilt(Collections.max(trunkTilts));

            double sway = (Collections.max(ankleX) - Collections.min(ankleX)) +
                    (Collections.max(ankleY) - Collections.min(ankleY)) +
                    (Collections.max(ankleZ) - Collections.min(ankleZ));
            req.setAnkleSwayDistance(sway);
        }

        return req;
    }
}