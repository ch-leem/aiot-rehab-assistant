package com.example.iot.pose.metrics;

public enum PoseMetricType {
    // Upper
    SHOULDER_FLEXION_L,
    SHOULDER_FLEXION_R,
    ELBOW_EXTENSION_L,
    ELBOW_EXTENSION_R,
    TRUNK_LEAN,              // 상체 기울기(수직 대비)
    SHOULDER_TILT,           // 어깨 수평도

    // Lower
    ANKLE_PLANTARFLEXION_L,
    ANKLE_PLANTARFLEXION_R,
    KNEE_FLEXION_L,
    KNEE_FLEXION_R,
    PELVIS_TILT,             // 골반 수평도
    TRUNK_LATERAL_LEAN,      // 상체 측방 기울기(센터-센터)
    ANKLE_INVERSION_L,
    ANKLE_INVERSION_R,
    HIP_FLEXION_L,
    HIP_FLEXION_R
}