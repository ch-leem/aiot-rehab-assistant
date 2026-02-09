package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Getter @Setter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Table(name = "exercise_goal")
public class ExerciseGoal {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long goalId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "exercise_id", nullable = false)
    private Exercise exercise;

    @Column(nullable = false, length = 20)
    private String goalType; // "MAIN", "SUB"

    @Column(nullable = false, length = 100)
    private String name;

    @Column(nullable = false, length = 20)
    private String targetType; // "ANGLE", "PRESSURE" 등

    @Column(nullable = false)
    private Double targetValue;

    private Double threshold;

    @Column(length = 20)
    private String unit;

    public ExerciseGoal(Exercise exercise, String goalType, String name, String targetType, Double targetValue, String unit) {
        this.exercise = exercise;
        this.goalType = goalType;
        this.name = name;
        this.targetType = targetType;
        this.targetValue = targetValue;
        this.unit = unit;
    }
}