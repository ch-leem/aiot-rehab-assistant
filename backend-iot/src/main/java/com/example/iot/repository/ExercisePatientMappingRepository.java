package com.example.iot.repository;

import com.example.iot.domain.ExercisePatientMapping;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ExercisePatientMappingRepository extends JpaRepository<ExercisePatientMapping, Long> {
}
