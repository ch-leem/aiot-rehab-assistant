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
    public void run(String... args) {

        if (exerciseRepository.count() > 0) return;

        // 1. 상체: 양팔 들어올리기
        Exercise armRaise = new Exercise(
                "양팔 들어올리기",
                "어깨만을 사용하여 팔을 쭉 편 채 위로 들어올리는 재활 운동입니다.",
                "어깨 관절 가동 범위 확보",
                "몸을 기울이거나 반동을 주지 마세요"
        );
        exerciseRepository.save(armRaise);

        // 생성자 순서: exercise, goalType, name, targetType, targetValue, unit
        // 현재 초기값에 배정된 값들은 아무거나 작성한 값입니다.(추후 수정 필요)
        exerciseGoalRepository.saveAll(List.of(
                new ExerciseGoal(armRaise, "MAIN", "어깨 외전 각도", "ANGLE", 160.0, "deg"),
                new ExerciseGoal(armRaise, "SUB", "팔꿈치 굴곡 방지", "ANGLE", 180.0, "deg"),
                new ExerciseGoal(armRaise, "SUB", "상체 기울기", "ANGLE", 0.0, "deg")
        ));

        // 2. 하체: 발판 밟기
        Exercise stepPress = new Exercise(
                "발판 밟기",
                "환측 발을 발판 위에 올리고 힘을 주어 누르는 운동입니다.",
                "하체 근력 및 체중 지지 능력 강화",
                "디딤발에 힘을 주지 말고 환측 발의 힘으로만 누르세요"
        );
        exerciseRepository.save(stepPress);

        exerciseGoalRepository.saveAll(List.of(
                new ExerciseGoal(stepPress, "MAIN", "발판 압력", "PRESSURE", 50.0, "kg"),
                new ExerciseGoal(stepPress, "SUB", "디딤발 하중 비율", "RATIO", 20.0, "%"),
                new ExerciseGoal(stepPress, "SUB", "유지 시간", "TIME", 5.0, "sec")
        ));

        System.out.println("데모용 상/하체 운동 마스터 데이터 설정 완료");
    }
}