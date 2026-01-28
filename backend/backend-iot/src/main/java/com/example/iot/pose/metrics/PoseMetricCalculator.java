package com.example.iot.pose.metrics;

import com.example.iot.pose.config.PoseThresholds;
import com.example.iot.pose.math.PoseMath;
import com.example.iot.pose.model.Point2D;
import com.example.iot.pose.model.PoseFrame;
import com.example.iot.pose.model.PoseLandmark;
import org.springframework.stereotype.Component;

@Component
public class PoseMetricCalculator {

    private final PoseThresholds thresholds;

    public PoseMetricCalculator(PoseThresholds thresholds) {
        this.thresholds = thresholds;
    }

    public PoseMetrics calculate(PoseFrame frame) {
        double minConf = thresholds.getMinConf();

        var m = new PoseMetrics();

        // points
        Point2D ls = frame.get(PoseLandmark.LEFT_SHOULDER);
        Point2D rs = frame.get(PoseLandmark.RIGHT_SHOULDER);
        Point2D le = frame.get(PoseLandmark.LEFT_ELBOW);
        Point2D re = frame.get(PoseLandmark.RIGHT_ELBOW);
        Point2D lw = frame.get(PoseLandmark.LEFT_WRIST);
        Point2D rw = frame.get(PoseLandmark.RIGHT_WRIST);

        Point2D lh = frame.get(PoseLandmark.LEFT_HIP);
        Point2D rh = frame.get(PoseLandmark.RIGHT_HIP);
        Point2D lk = frame.get(PoseLandmark.LEFT_KNEE);
        Point2D rk = frame.get(PoseLandmark.RIGHT_KNEE);
        Point2D la = frame.get(PoseLandmark.LEFT_ANKLE);
        Point2D ra = frame.get(PoseLandmark.RIGHT_ANKLE);

        Point2D lHeel = frame.get(PoseLandmark.LEFT_HEEL);
        Point2D rHeel = frame.get(PoseLandmark.RIGHT_HEEL);
        Point2D lToe  = frame.get(PoseLandmark.LEFT_BIG_TOE);
        Point2D rToe  = frame.get(PoseLandmark.RIGHT_BIG_TOE);

        // centers
        Point2D sc = PoseMath.center(ls, rs);
        Point2D hc = PoseMath.center(lh, rh);

        // ---- Upper metrics ----
        // 어깨 굴곡: Hip - Shoulder - Wrist
        m.put(PoseMetricType.SHOULDER_FLEXION_L, PoseMath.angleABC(lh, ls, lw, minConf));
        m.put(PoseMetricType.SHOULDER_FLEXION_R, PoseMath.angleABC(rh, rs, rw, minConf));

        // 팔꿈치 신전도: Shoulder - Elbow - Wrist
        m.put(PoseMetricType.ELBOW_EXTENSION_L, PoseMath.angleABC(ls, le, lw, minConf));
        m.put(PoseMetricType.ELBOW_EXTENSION_R, PoseMath.angleABC(rs, re, rw, minConf));

        // 상체 기울기(수직 대비): HipCenter -> ShoulderCenter
        m.put(PoseMetricType.TRUNK_LEAN, PoseMath.angleLineVsVertical(hc, sc, minConf));

        // 어깨 수평도: LShoulder - RShoulder vs Horizontal
        m.put(PoseMetricType.SHOULDER_TILT, PoseMath.angleLineVsHorizontal(ls, rs, minConf));

        // ---- Lower metrics ----
        // 발목 족저굴곡: Knee - Ankle - Toe
        m.put(PoseMetricType.ANKLE_PLANTARFLEXION_L, PoseMath.angleABC(lk, la, lToe, minConf));
        m.put(PoseMetricType.ANKLE_PLANTARFLEXION_R, PoseMath.angleABC(rk, ra, rToe, minConf));

        // 무릎 굴곡: Hip - Knee - Ankle
        m.put(PoseMetricType.KNEE_FLEXION_L, PoseMath.angleABC(lh, lk, la, minConf));
        m.put(PoseMetricType.KNEE_FLEXION_R, PoseMath.angleABC(rh, rk, ra, minConf));

        // 골반 수평도: LHip - RHip vs Horizontal
        m.put(PoseMetricType.PELVIS_TILT, PoseMath.angleLineVsHorizontal(lh, rh, minConf));

        // 상체 측방 기울기(센터-센터): HipCenter -> ShoulderCenter 수직 대비
        m.put(PoseMetricType.TRUNK_LATERAL_LEAN, PoseMath.angleLineVsVertical(hc, sc, minConf));

        // 발목 내/외번(heel 기반): Knee - Ankle - Heel
        m.put(PoseMetricType.ANKLE_INVERSION_L, PoseMath.angleABC(lk, la, lHeel, minConf));
        m.put(PoseMetricType.ANKLE_INVERSION_R, PoseMath.angleABC(rk, ra, rHeel, minConf));

        // 고관절 굴곡: Shoulder - Hip - Knee
        m.put(PoseMetricType.HIP_FLEXION_L, PoseMath.angleABC(ls, lh, lk, minConf));
        m.put(PoseMetricType.HIP_FLEXION_R, PoseMath.angleABC(rs, rh, rk, minConf));

        return m;
    }
}
