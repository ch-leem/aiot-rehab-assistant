package com.example.user.dto;

import com.example.iot.domain.ExercisePatientMapping;
import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class PatientExerciseConfigResponse {
    private Long mappingId;
    private Long exerciseId;
    private String exerciseName;
    private String exerciseDescription;
    private String side;            // 환부 방향 (LEFT, RIGHT 등)

    private Long goalId;            // 목표 고유 ID
    private String goalName;        // 목표 명칭 (예: 팔꿈치 굴곡)
    private String targetType;      // ANGLE, SENSOR 등
    private Double targetValue;     // 설정된 목표 수치 (맞춤값이 있으면 맞춤값, 없으면 기본값)
    private String unit;            // 단위 (deg, m/s2 등)

    public static PatientExerciseConfigResponse from(ExercisePatientMapping mapping) {
        // 맞춤 설정값이 있으면 사용하고, 없으면 해당 목표의 기본 표준값을 가져옵니다.
        Double finalTargetValue = mapping.getCustomTargetValue() != null
                ? mapping.getCustomTargetValue()
                : mapping.getExerciseGoal().getTargetValue();

        return PatientExerciseConfigResponse.builder()
                .mappingId(mapping.getId())
                .exerciseId(mapping.getExercise().getId())
                .exerciseName(mapping.getExercise().getName())
                .exerciseDescription(mapping.getExercise().getDescription())
                .side(mapping.getSide() != null ? mapping.getSide().name() : null)
                // 상세 목표 정보 매핑
                .goalId(mapping.getExerciseGoal().getGoalId())
                .goalName(mapping.getExerciseGoal().getName())
                .targetType(mapping.getExerciseGoal().getTargetType())
                .targetValue(finalTargetValue)
                .unit(mapping.getExerciseGoal().getUnit())
                .build();
    }
}