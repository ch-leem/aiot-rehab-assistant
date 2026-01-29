package com.example.iot.init;

import com.example.iot.domain.Exercise;
import com.example.iot.domain.ExerciseGoal;
import com.example.iot.repository.ExerciseGoalRepository;
import com.example.iot.repository.ExerciseRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Component
@RequiredArgsConstructor
public class ExerciseMasterInitializer implements CommandLineRunner {

    private final ExerciseRepository exerciseRepository;
    private final ExerciseGoalRepository exerciseGoalRepository;

    @Override
    @Transactional
    // 각 운동의 목표 계산을 위한 측정값의 수치와 단위는 임의로 설정되었습니다
    public void run(String... args) {
        if (exerciseRepository.count() > 0) return;

        // 1. 어깨 굴곡 운동 (Shoulder Flexion)
        Exercise shoulderFlexion = new Exercise(
                "어깨 굴곡 운동",
                "팔을 편 상태로 전방을 향해 들어올리는 운동입니다.",
                "어깨 가동 범위 확보 및 상지 근지구력 강화",
                "팔꿈치가 굽혀지거나 허리가 뒤로 젖혀지지 않게 주의하세요."
        );
        exerciseRepository.save(shoulderFlexion);

        exerciseGoalRepository.saveAll(List.of(
                // MAIN: 성취도 및 유지 능력
                new ExerciseGoal(shoulderFlexion, "MAIN", "어깨 외전 각도", "ANGLE", 160.0, "deg"),
                new ExerciseGoal(shoulderFlexion, "MAIN", "팔꿈치 신전 상태", "ANGLE", 180.0, "deg"),
                // new ExerciseGoal(shoulderFlexion, "MAIN", "목표 각도 유지 시간", "TIME", 5.0, "sec"),

                // SUB: 보상 동작 억제 (0에 가까울수록 고득점인 감점형 지표들)
                // 가속도 값은 추후 조정 필요
                new ExerciseGoal(shoulderFlexion, "SUB", "상체 앞뒤 기울기", "ANGLE", 0.0, "deg"),
                new ExerciseGoal(shoulderFlexion, "SUB", "어깨 수평 불균형", "ANGLE", 0.0, "deg"),
                new ExerciseGoal(shoulderFlexion, "SUB", "수행 가속도", "ACCEL", 0.0, "m/s²")
        ));

        // 2. 비대칭 체중 부하 운동 (Asymmetrical Weight Bearing)
        Exercise weightBearing = new Exercise(
                "비대칭 체중 부하 운동",
                "마비측 다리에 체중을 싣고 균형을 유지하는 운동입니다.",
                "하지 근력 강화 및 심부 안정성 개선",
                "골반이 옆으로 빠지지 않게 유지하며 마비측 발바닥 전체로 지면을 누르세요."
        );
        exerciseRepository.save(weightBearing);

        exerciseGoalRepository.saveAll(List.of(
                // MAIN: 하중 지지 및 유지 능력
                new ExerciseGoal(weightBearing, "MAIN", "마비측 발판 압력", "PRESSURE", 60.0, "%"),

                // SUB: 자세 안정성 (0에 가까울수록 고득점인 감점형 지표들)
                new ExerciseGoal(weightBearing, "SUB", "골반 수평 편차", "ANGLE", 0.0, "deg"),
                new ExerciseGoal(weightBearing, "SUB", "비마비측 발목 흔들림", "STABILITY", 0.0, "score"),
                new ExerciseGoal(weightBearing, "SUB", "상체 앞뒤 기울기", "ANGLE", 0.0, "deg")

        ));

        System.out.println("재활 운동 마스터 데이터(어깨 굴곡/체중 부하) 설정 완료");
    }
}