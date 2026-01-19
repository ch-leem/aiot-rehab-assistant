package com.example.iot.repository;

import com.example.iot.domain.ExerciseSensorMapping;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ExerciseSensorMappingRepository extends JpaRepository<ExerciseSensorMapping, Long> {

    //운동 별 필요한 센서 조회
    List<ExerciseSensorMapping> findByExercise_Id(Long exerciseId);
    //운동 별 필요한 센서 있는지 확인
    boolean existsByExercise_IdAndSensor_Id(Long exerciseId, String sensorId);
}
