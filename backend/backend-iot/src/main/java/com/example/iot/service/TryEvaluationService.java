package com.example.iot.service;

import com.example.iot.pose.metrics.PoseMetricCalculator;
import com.example.iot.pose.metrics.PoseMetricType;
import com.example.iot.pose.model.PoseFrame;
import org.springframework.stereotype.Service;

@Service
public class TryEvaluationService {

    private final PoseMetricCalculator metricCalculator;

    public TryEvaluationService(PoseMetricCalculator metricCalculator) {
        this.metricCalculator = metricCalculator;
    }

    public void evaluateOneFrame(PoseFrame frame) {
        var metrics = metricCalculator.calculate(frame);

        // 예: 필요한 값 꺼내서 로직 작성
        Double trunkLean = metrics.get(PoseMetricType.TRUNK_LEAN);
        Double kneeFlexL = metrics.get(PoseMetricType.KNEE_FLEXION_L);

        // TODO: 임계값 기반 성공/실패 판정, 피드백 생성, DB 저장 등
        // if(trunkLean != null && trunkLean > 15) { ... }
    }
}