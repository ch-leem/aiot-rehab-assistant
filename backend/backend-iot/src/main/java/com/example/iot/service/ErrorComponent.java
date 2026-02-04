package com.example.iot.service;

public class ErrorComponent {

    public static int errorScoreFromAbsErrorAgg(
            double target, //target 목표가 되는 값 180
            double threshold, //threshold 값 이 정도는 넘어야 한다. 150
            long cnt, //몇 번 했는지
            double sum, //전체 값,
            boolean isJitter // jitter일 경우 true 입력
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

        double offset = 0.0;
        //점수
        if(isJitter) {
            perDegreeScore = 1.0;
        }
        double score = 100.0 +  meanE * perDegreeScore;

        // 점수 범위 제한
        return (int) score;
    }

//    private static double clamp01_100(double v) {
//        return Math.max(0.0, Math.min(100.0, v));
//    }

}
