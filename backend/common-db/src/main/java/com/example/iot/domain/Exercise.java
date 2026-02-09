package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import java.time.LocalDateTime;

@Entity
@Table(name = "exercise")
@Getter @Setter
public class Exercise {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "exercise_id")
    private Long id;

    @Column(nullable = false, length = 100)
    private String name;

    @Column(length = 500)
    private String description;

    @Column(name = "precautions", length = 1000) // 운동 시 주의사항
    private String precautions;

    @Column(name = "posture_guide", length = 1000) // 자세 확인 시 출력할 가이드 멘트
    private String postureGuide;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    protected Exercise() {}

    public Exercise(String name, String description, String precautions, String postureGuide) {
        this.name = name;
        this.description = description;
        this.precautions = precautions;
        this.postureGuide = postureGuide;
        this.createdAt = LocalDateTime.now();
    }

    @PrePersist
    public void prePersist() {
        if (createdAt == null) createdAt = LocalDateTime.now();
    }
}