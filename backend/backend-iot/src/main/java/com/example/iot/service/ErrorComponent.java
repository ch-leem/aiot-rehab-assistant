package com.example.iot.service;

public class ErrorComponent {

    public static int errorScoreFromAbsErrorAgg(
            double target,
            double threshold,
            long cnt,
            double sum
    ) {
        // 방어 로직
        if (cnt <= 0) return 0;

        double  denom = target - threshold;

        if(denom == 0.0) {
            denom = 1;
        }

        //1도 점수
        double perDegreeScore = Math.abs( 30.0 / denom );

        //error 평균
        double meanE =  (sum - (threshold * cnt)) / (double) cnt ; // mean(E)
        //점수
        double score = 100.0 +  meanE * perDegreeScore;

        // 점수 범위 제한
        return Math.min( 100, (int) score);
    }

//    private static double clamp01_100(double v) {
//        return Math.max(0.0, Math.min(100.0, v));
//    }

}
