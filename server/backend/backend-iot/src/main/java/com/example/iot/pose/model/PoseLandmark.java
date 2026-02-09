package com.example.iot.pose.model;

import java.util.Map;

public enum PoseLandmark {

    NOSE(0),
    LEFT_EYE(1), RIGHT_EYE(2),
    LEFT_EAR(3), RIGHT_EAR(4),

    LEFT_SHOULDER(5), RIGHT_SHOULDER(6),
    LEFT_ELBOW(7), RIGHT_ELBOW(8),
    LEFT_WRIST(9), RIGHT_WRIST(10),

    LEFT_HIP(11), RIGHT_HIP(12),
    LEFT_KNEE(13), RIGHT_KNEE(14),
    LEFT_ANKLE(15), RIGHT_ANKLE(16),

    // Foot extra (너가 가진 확장 포인트)
    LEFT_HEEL(17),
    RIGHT_HEEL(18),
    LEFT_BIG_TOE(19),
    RIGHT_BIG_TOE(20);

    private final int idx;

    PoseLandmark(int idx) {
        this.idx = idx;
    }

    public int idx() {
        return idx;
    }

    public Point2D getFrom(Map<Integer, Point2D> keypoints) {
        return keypoints.get(idx);
    }
}