package com.example.iot.repository;

import com.example.iot.domain.ExerciseJointMapping;
import com.example.iot.domain.ExerciseSensorMapping;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ExerciseJointMappingRepository extends JpaRepository<ExerciseJointMapping, Long> {

    //운동 별 필요한 Joint 조회
    List<ExerciseJointMapping> findByExercise_Id(Long exerciseId);
    //운동 별 필요한 Joint가 있는지 확인
    boolean existsByExercise_IdAndJoint_Id(Long exerciseId, String jointId);

}
