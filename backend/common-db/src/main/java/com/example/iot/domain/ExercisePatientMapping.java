package com.example.iot.domain;

import com.example.iot.domain.constant.Side;
import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "exercise_patient_mapping")
@Getter @Setter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ExercisePatientMapping {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "mapping_id")
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "exercise_id", nullable = false)
    private Exercise exercise;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "patient_id", nullable = false)
    private Patient patient;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "goal_id", nullable = false)
    private ExerciseGoal exerciseGoal;

    @Enumerated(EnumType.STRING)
    @Column(name = "side", length = 20)
    private Side side;

    @Column(name = "custom_target_value")
    private Double customTargetValue;

    public ExercisePatientMapping(Exercise exercise, Patient patient, ExerciseGoal goal, Side side, Double customTargetValue) {
        this.exercise = exercise;
        this.patient = patient;
        this.exerciseGoal = goal;
        this.side = side;
        this.customTargetValue = customTargetValue;
    }
}