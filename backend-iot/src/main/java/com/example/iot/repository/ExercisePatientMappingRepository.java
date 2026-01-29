package com.example.iot.repository;

import com.example.iot.domain.ExercisePatientMapping;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ExercisePatientMappingRepository extends JpaRepository<ExercisePatientMapping, Long> {

    //환자 id에 할당된 현재 운동 조회
    List<ExercisePatientMapping> findByPatient_Id(Long patientId);
    //현재 해야하는 운동 있는지 판단
    boolean existsByExercise_IdAndPatient_Id(Long exerciseId, Long patientId);
}
