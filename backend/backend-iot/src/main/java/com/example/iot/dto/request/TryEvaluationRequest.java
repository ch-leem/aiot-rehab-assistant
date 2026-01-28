package com.example.iot.dto.request;

import lombok.*;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class TryEvaluationRequest {
    // 1. 어깨 굴곡 운동 관련 (Main)
    private Double maxShoulderFlexionAngle;   // 어깨 외전 각도 (Max)
    private Double avgElbowExtensionAngle;   // 팔꿈치 신전 상태 (Avg)

    // 2. 비대칭 체중 부하 운동 관련 (Main)
    private Double maxPressure;      // 마비측 발판 압력 (Max - power 기반)

    // 3. 공통 보상 작용 및 안정성 지표 (Sub)
    private Double avgTrunkForwardTilt;       // 상체 앞뒤 기울기 (Avg)
    private Double avgShoulderLevelDiff;      // 어깨 수평 불균형 (Avg)
    private Double avgPelvisLevelDiff;        // 골반 수평 편차 (Avg)
    private Double avgMovementAcceleration;   // 수행 가속도 (Avg)
    private Double ankleSwayDistance;         // 비마비측 발목 흔들림 (Distance - XYZ 편차)

    // 기타 (확장성을 위해 남겨둠)
    private Double avgTrunkLateralTilt;

    /**
     * 목표 명칭에 따라 적절한 분석 수치를 반환합니다.
     * 로직 수정 시 이 메서드의 매핑만 변경하면 점수 계산 로직(TryService)은 그대로 유지됩니다.
     */
    public double getValueByGoalName(String goalName) {
        if (goalName == null) return 0.0;
        return switch (goalName) {
            case "어깨 외전 각도" -> nvl(maxShoulderFlexionAngle);
            case "팔꿈치 신전 상태" -> nvl(avgElbowExtensionAngle);
            case "상체 앞뒤 기울기" -> nvl(avgTrunkForwardTilt); // 평균값으로 매핑 변경
            case "어깨 수평 불균형" -> nvl(avgShoulderLevelDiff);
            case "수행 가속도" -> nvl(avgMovementAcceleration); // 평균값으로 매핑 변경
            case "마비측 발판 압력" -> nvl(maxPressure);
            case "골반 수평 편차" -> nvl(avgPelvisLevelDiff);
            case "비마비측 발목 흔들림" -> nvl(ankleSwayDistance);
            default -> 0.0;
        };
    }

    private double nvl(Double value) {
        return value == null ? 0.0 : value;
    }
}