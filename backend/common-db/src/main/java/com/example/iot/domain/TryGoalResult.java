package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "try_goal_result")
@Getter
@Setter
@Builder
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
public class TryGoalResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "result_id")
    private Long id;

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