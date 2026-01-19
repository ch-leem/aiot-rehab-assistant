package com.example.iot.repository;

import com.example.iot.domain.ExerciseSensorMapping;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ExerciseSensorMappingRepository extends JpaRepository<ExerciseSensorMapping, Long> {
}
