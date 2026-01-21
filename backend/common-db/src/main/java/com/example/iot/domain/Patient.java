package com.example.iot.domain;

import com.example.iot.domain.constant.Gender;      // 생성 필요
import com.example.iot.domain.constant.RehabPhase; // 생성 필요
import jakarta.persistence.*;
import lombok.*;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "patient")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
@Builder
@EntityListeners(AuditingEntityListener.class)
public class Patient {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "patient_id")
    private Long id;

    @Column(nullable = false, length = 100)
    private String name;

    private LocalDate birthDate;

    @Enumerated(EnumType.STRING)
    @Column(length = 20)
    private Gender gender;

    // 명세서에는 없지만 코드에 있던 필드 (필요시 명세서 업데이트)
    private String diseaseName;

    @Enumerated(EnumType.STRING)
    private RehabPhase rehabPhase;

    @CreatedDate // Spring Data JPA가 자동으로 시간을 할당 (수동 설정 불필요)
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    public void updateInfo(String name, String diseaseName, RehabPhase rehabPhase) {
        this.name = name;
        this.diseaseName = diseaseName;
        this.rehabPhase = rehabPhase;
    }
}