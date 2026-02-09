package com.example.iot.repository;

import com.example.iot.domain.ExercisePatientMapping;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ExercisePatientMappingRepository extends JpaRepository<ExercisePatientMapping, Long> {

    @Query("""
        select m.exercise.id
        from ExercisePatientMapping m
        where m.patient.id = :patientId
    """)
    List<Long> findExerciseIdsByPatientId(@Param("patientId") Long patientId);

    // 환자에게 할당된 운동 매핑 전체
    List<ExercisePatientMapping> findByPatient_Id(Long patientId);
    //현재 해야하는 운동 있는지 판단
    boolean existsByExercise_IdAndPatient_Id(Long exerciseId, Long patientId);

    Optional<ExercisePatientMapping> findByPatient_IdAndExercise_Id(Long patientId, Long exerciseId);

    List<ExercisePatientMapping> findAllByPatient_IdAndExercise_Id(Long patientId, Long exerciseId);
}
