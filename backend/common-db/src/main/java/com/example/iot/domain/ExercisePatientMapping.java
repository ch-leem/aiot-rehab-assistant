package com.example.iot.domain;

import com.example.iot.domain.constant.Side;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Entity
@Table(name = "exercise_patient_mapping")
@Getter @Setter
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

    @Enumerated(EnumType.STRING)
    @Column(name = "side", length = 20)
    private Side side;

    @Column(name = "goal_vision", length = 255)
    private String goalVision;

    @Column(name = "goal_sensor", length = 255)
    private String goalSensor;

    protected ExercisePatientMapping() {}

    public ExercisePatientMapping(Exercise exercise, Patient patient, Side side) {
        this.exercise = exercise;
        this.patient = patient;
        this.side = side;
    }
}