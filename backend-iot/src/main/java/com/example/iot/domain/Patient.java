package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Getter @Setter
public class Patient {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long PatientId;
    private String Name;
    private LocalDate BirthDate;
    private String Gender;
    private String RehabPhase;
    private LocalDateTime CreatedAt = LocalDateTime.now();
}