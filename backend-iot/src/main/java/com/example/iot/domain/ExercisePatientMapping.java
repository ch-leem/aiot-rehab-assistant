package com.example.iot.domain;

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
    @JoinColumn(name = "exercise_id")
    private Exercise exercise;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "patient_id")
    private Patient patient;

    private String side; // left, right, both
    private String goalVision;
    private String goalSensor;

    protected ExercisePatientMapping() {}

    public ExercisePatientMapping(Exercise exercise, Patient patient, String side) {
        this.exercise = exercise;
        this.patient = patient;
        this.side = side;
    }
}