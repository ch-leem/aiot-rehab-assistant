package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "patient")
@Getter @Setter
public class Patient {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "patient_id")
    private Long id;

    @Column(nullable = false, length = 100)
    private String name;

    private LocalDate birthDate;
    private String gender;
    private String rehabPhase;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    protected Patient() {}

    public Patient(String name, LocalDate birthDate, String gender, String rehabPhase) {
        this.name = name;
        this.birthDate = birthDate;
        this.gender = gender;
        this.rehabPhase = rehabPhase;
        this.createdAt = LocalDateTime.now();
    }
}