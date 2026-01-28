package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Entity
@Table(name = "exercise_sensor_mapping")
@Getter @Setter
public class ExerciseSensorMapping {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "mapping_id")
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "exercise_id", nullable = false)
    private Exercise exercise;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "sensor_id", nullable = false)
    private Sensor sensor;

    @Column(name = "role", length = 255)
    private String role;

    protected ExerciseSensorMapping() {}

    public ExerciseSensorMapping(Exercise exercise, Sensor sensor, String role) {
        this.exercise = exercise;
        this.sensor = sensor;
        this.role = role;
    }
}