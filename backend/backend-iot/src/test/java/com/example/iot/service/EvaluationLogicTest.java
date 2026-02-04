package com.example.iot.service;

import com.example.iot.dto.request.TryEvaluationRequest;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

// @SpringBootTest를 제거합니다. (의존성 문제를 피하기 위함)
class EvaluationLogicTest {

    private FrameAnalyzer frameAnalyzer;

    @BeforeEach
    void setUp() {
        // 의존성이 있는 ObjectMapper를 직접 생성해서 주입합니다.
        this.frameAnalyzer = new FrameAnalyzer(new ObjectMapper());
    }

    @Test
    @DisplayName("Redis Map 데이터가 DTO로 잘 변환되는지 확인")
    void analyzeSummaryTest() {
        Map<Object, Object> mockAgg = new HashMap<>();
        mockAgg.put("max.power", "55.5");
        mockAgg.put("sum.strength", "20.0");
        mockAgg.put("count.strength", "10");
        mockAgg.put("sum.elbow_extension", "1750.0");
        mockAgg.put("count.elbow_extension", "10");

        mockAgg.put("max.l_ankle_x", "12.0");
        mockAgg.put("min.l_ankle_x", "10.0");
        mockAgg.put("max.l_ankle_y", "5.0");
        mockAgg.put("min.l_ankle_y", "5.0");
        mockAgg.put("max.l_ankle_z", "1.0");
        mockAgg.put("min.l_ankle_z", "1.0");

        // 로직 실행 (RIGHT 환측일 때 비마비측 l_ankle 분석)
        TryEvaluationRequest result = frameAnalyzer.analyzeSummary(null, mockAgg, "RIGHT");

        // DTO의 필드명에 맞춰 assertEquals 실행
        assertEquals(55.5, result.getMaxPressure());
        assertEquals(2.0, result.getAvgMovementAcceleration());
        assertEquals(175.0, result.getAvgElbowExtensionAngle());
        assertEquals(2.0, result.getAnkleSwayDistance());
    }

    @Test
    @DisplayName("목표 명칭과 데이터 필드 매핑 확인")
    void goalMappingTest() {
        TryEvaluationRequest req = new TryEvaluationRequest();
        req.setMaxPressure(60.0);
        req.setAvgMovementAcceleration(1.2);

        assertEquals(60.0, req.getValueByGoalName("마비측 발판 압력"));
        assertEquals(1.2, req.getValueByGoalName("수행 가속도"));
    }
}