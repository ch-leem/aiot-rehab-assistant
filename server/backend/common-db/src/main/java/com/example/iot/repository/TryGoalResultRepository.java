package com.example.iot.repository;

import com.example.iot.domain.Try;
import com.example.iot.domain.TryGoalResult;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface TryGoalResultRepository extends JpaRepository<TryGoalResult, Long> {

    // 특정 시도(Try)에 대한 모든 상세 목표 결과들을 조회하고 싶을 때 사용
    List<TryGoalResult> findByExerciseTry(Try exerciseTry);

    // 특정 목표(ExerciseGoal)의 결과들만 모아서 통계를 내고 싶을 때 사용
    // List<TryGoalResult> findByExerciseGoal_Id(Long goalId);
}