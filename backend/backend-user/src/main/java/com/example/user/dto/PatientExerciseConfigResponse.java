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
    private String side;        // 환부 방향 (Left/Right 등)
    private String goalVision;  // 맞춤형 비전 목표
    private String goalSensor;  // 맞춤형 센서 목표

    public static PatientExerciseConfigResponse from(ExercisePatientMapping mapping) {
        return PatientExerciseConfigResponse.builder()
                .mappingId(mapping.getId())
                .exerciseId(mapping.getExercise().getId())
                .exerciseName(mapping.getExercise().getName())
                .exerciseDescription(mapping.getExercise().getDescription())
                .side(mapping.getSide() != null ? mapping.getSide().name() : null)
                .goalVision(mapping.getGoalVision())
                .goalSensor(mapping.getGoalSensor())
                .build();
    }
}