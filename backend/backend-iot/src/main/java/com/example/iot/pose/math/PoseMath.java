package com.example.iot.pose.math;

import com.example.iot.pose.model.Point2D;

public final class PoseMath {

    private PoseMath() {}

    public static boolean valid(Point2D p, double minConf) {
        return p != null
                && p.conf() >= minConf
                && !Double.isNaN(p.x()) && !Double.isNaN(p.y());
    }

    public static Point2D center(Point2D a, Point2D b) {
        if (a == null || b == null) return null;
        return new Point2D(
                (a.x() + b.x()) / 2.0,
                (a.y() + b.y()) / 2.0,
                Math.min(a.conf(), b.conf())
        );
    }

    /** 관절각: A-B-C (B에서의 각도), deg */
    public static Double angleABC(Point2D A, Point2D B, Point2D C, double minConf) {
        if (!valid(A, minConf) || !valid(B, minConf) || !valid(C, minConf)) return null;

        double ux = A.x() - B.x();
        double uy = A.y() - B.y();
        double vx = C.x() - B.x();
        double vy = C.y() - B.y();

        double uNorm = Math.hypot(ux, uy);
        double vNorm = Math.hypot(vx, vy);
        if (uNorm < 1e-9 || vNorm < 1e-9) return null;

        double dot = ux * vx + uy * vy;
        double cos = dot / (uNorm * vNorm);

        // float 오차 클램프
        cos = Math.max(-1.0, Math.min(1.0, cos));

        double rad = Math.acos(cos);
        return Math.toDegrees(rad);
    }

    /** 라인(P1->P2) vs Horizontal 각도(0~90), deg */
    public static Double angleLineVsHorizontal(Point2D p1, Point2D p2, double minConf) {
        if (!valid(p1, minConf) || !valid(p2, minConf)) return null;

        double dx = p2.x() - p1.x();
        double dy = p2.y() - p1.y();

        double deg = Math.abs(Math.toDegrees(Math.atan2(dy, dx))); // 0~180
        if (deg > 90.0) deg = 180.0 - deg; // 0~90으로 접기
        return deg;
    }

    /** 라인(P1->P2) vs Vertical 각도(0~90), deg */
    public static Double angleLineVsVertical(Point2D p1, Point2D p2, double minConf) {
        if (!valid(p1, minConf) || !valid(p2, minConf)) return null;

        double dx = p2.x() - p1.x();
        double dy = p2.y() - p1.y();

        // 수직과의 각 = atan2(|dx|, |dy|)
        return Math.toDegrees(Math.atan2(Math.abs(dx), Math.abs(dy)));
    }
}
