package com.example.iot.dto.request;

import lombok.*;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class TryEvaluationRequest {
    private Double maxShoulderFlexionAngle;
    private Double avgElbowExtensionAngle;
    private Double maxTrunkForwardTilt;
    private Double avgShoulderLevelDiff;
    private Double maxMovementAcceleration;
    private Double maxFootPlatePressure;
    private Double avgPelvisLevelDiff;
    private Double ankleSwayDistance;
    private Double avgTrunkLateralTilt;

    public double getValueByGoalName(String goalName) {
        if (goalName == null) return 0.0;
        return switch (goalName) {
            case "어깨 외전 각도" -> nvl(maxShoulderFlexionAngle);
            case "팔꿈치 신전 상태" -> nvl(avgElbowExtensionAngle);
            case "상체 앞뒤 기울기" -> nvl(maxTrunkForwardTilt);
            case "어깨 수평 불균형" -> nvl(avgShoulderLevelDiff);
            case "수행 가속도" -> nvl(maxMovementAcceleration);
            case "마비측 발판 압력" -> nvl(maxFootPlatePressure);
            case "골반 수평 편차" -> nvl(avgPelvisLevelDiff);
            case "비마비측 발목 흔들림" -> nvl(ankleSwayDistance);
            default -> 0.0;
        };
    }

    private double nvl(Double value) { return value == null ? 0.0 : value; }
}