package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "try_goal_result")
@Getter @Setter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class TryGoalResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "result_id")
    private Long id;

    // 'try'는 자바 예약어이므로 'exerciseTry' 또는 'tryEntity'로 변경
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "try_id", nullable = false)
    private Try exerciseTry;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "goal_id", nullable = false)
    private ExerciseGoal exerciseGoal;

    @Column(name = "measured_value", nullable = false)
    private Double measuredValue;

    @Column(name = "achievement_rate", nullable = false)
    private Double achievementRate;

    /**
     * 생성자
     */
    public TryGoalResult(Try exerciseTry, ExerciseGoal goal, Double measuredValue, Double achievementRate) {
        this.exerciseTry = exerciseTry;
        this.exerciseGoal = goal;
        this.measuredValue = measuredValue;
        this.achievementRate = achievementRate;
    }

    public static TryGoalResult createResult(Try exerciseTry, ExerciseGoal goal, Double measuredValue, Double achievementRate) {
        return new TryGoalResult(exerciseTry, goal, measuredValue, achievementRate);
    }
}