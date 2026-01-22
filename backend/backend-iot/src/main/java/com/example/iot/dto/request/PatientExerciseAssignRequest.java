package com.example.iot.dto.request;

import com.example.iot.domain.constant.Side;

public class PatientExerciseAssignRequest {

    private Side side;              // LEFT / RIGHT
    private String goalSensor;     // nullable
    private String goalVision;     // nullable

    public Side getSide() {
        return side;
    }

    public String getGoalSensor() {
        return goalSensor;
    }

    public String getGoalVision() {
        return goalVision;
    }
}
