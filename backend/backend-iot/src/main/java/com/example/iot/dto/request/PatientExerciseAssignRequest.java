package com.example.iot.dto.request;

public class PatientExerciseAssignRequest {

    private String side;              // LEFT / RIGHT
    private String goalSensor;     // nullable
    private String goalVision;     // nullable

    public String getSide() {
        return side;
    }

    public String getGoalSensor() {
        return goalSensor;
    }

    public String getGoalVision() {
        return goalVision;
    }
}
