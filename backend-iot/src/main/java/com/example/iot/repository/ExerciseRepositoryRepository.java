package com.example.iot.repository;

import com.example.iot.domain.Exercise;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ExerciseRepositoryRepository extends JpaRepository<Exercise, Long> {
}
