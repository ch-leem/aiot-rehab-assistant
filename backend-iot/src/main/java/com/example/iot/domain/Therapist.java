package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import java.time.LocalDateTime;

@Entity
@Getter @Setter
public class Therapist {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long TherapistId;

    private String Name;
    private String LicenseNo;
    private LocalDateTime CreatedAt = LocalDateTime.now();
}