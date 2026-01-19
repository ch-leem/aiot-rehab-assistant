package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import java.time.LocalDateTime;

@Entity
@Getter @Setter
public class Exercise {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long ExerciseId;

    private String Name;

    @Column(columnDefinition = "TEXT")
    private String Description;

    private LocalDateTime CreatedAt = LocalDateTime.now();
}
