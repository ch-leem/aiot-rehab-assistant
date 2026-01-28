package com.example.iot.dto.request;

import com.example.iot.domain.constant.Side;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.util.List;

@Getter
@Setter
@NoArgsConstructor
public class PatientExerciseAssignRequest {

    // 어느 방향 운동인지 (LEFT, RIGHT, BOTH)
    private Side side;

    // 환자별 맞춤 목표치 리스트 (필요한 경우에만 포함)
    private List<CustomGoalRequest> customGoals;

    @Getter
    @Setter
    @NoArgsConstructor
    public static class CustomGoalRequest {
        private Long goalId;              // ExerciseGoal의 ID
        private Double customTargetValue; // 이 환자만을 위한 수정된 목표값
    }
}