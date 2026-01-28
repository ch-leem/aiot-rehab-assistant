package com.example.iot.repository;

import com.example.iot.domain.Exercise;
import com.example.iot.domain.ExerciseGoal;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ExerciseGoalRepository extends JpaRepository<ExerciseGoal, Long> {

    // Exercise 엔티티를 조건으로 해당 운동의 모든 목표 리스트를 조회합니다.
    List<ExerciseGoal> findByExercise(Exercise exercise);
}