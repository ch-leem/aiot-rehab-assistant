package com.example.iot.pose.model;

import java.time.Instant;
import java.util.Collections;
import java.util.Map;

public class PoseFrame {

    private final Instant timestamp;
    private final Map<Integer, Point2D> keypoints; // 표준 인덱스 기준

    public PoseFrame(Instant timestamp, Map<Integer, Point2D> keypoints) {
        this.timestamp = timestamp;
        this.keypoints = keypoints == null ? Collections.emptyMap() : keypoints;
    }

    public Instant timestamp() {
        return timestamp;
    }

    public Map<Integer, Point2D> keypoints() {
        return keypoints;
    }

    public Point2D get(PoseLandmark lm) {
        return lm.getFrom(keypoints);
    }
}