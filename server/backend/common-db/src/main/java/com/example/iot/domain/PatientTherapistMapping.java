package com.example.iot.domain;

import com.example.iot.domain.constant.PatientTherapistMappingStatus; // Enum 생성 필요
import jakarta.persistence.*;
import lombok.*;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.time.LocalDateTime;

@Entity
@Table(
        name = "patient_therapist_mapping",
        indexes = {
        @Index(name = "idx_mapping_patient", columnList = "patient_id"),
        @Index(name = "idx_mapping_therapist", columnList = "therapist_id"),
        @Index(name = "idx_mapping_status", columnList = "status")
    }
)
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
@EntityListeners(AuditingEntityListener.class) // 생성일 자동 기록용
public class PatientTherapistMapping {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "patient_id", nullable = false)
    private Patient patient;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "therapist_id", nullable = false)
    private Therapist therapist; // Therapist 엔티티가 있다는 가정

    // --- 추가 제안 컬럼 ---

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    @Builder.Default
    private PatientTherapistMappingStatus status = PatientTherapistMappingStatus.ACTIVE; // 관계 상태 (활성/종료)

    @CreatedDate
    @Column(updatable = false)
    private LocalDateTime assignedAt; // 배정된 일시

    private String memo; // 치료사가 해당 환자를 담당하게 된 특이사항(예: 주치의 지정 등)

    // 관계 종료 시 기록
    private LocalDateTime terminatedAt;

    // 상태 변경 메서드
    public void terminate() {
        this.status = PatientTherapistMappingStatus.TERMINATED;
        this.terminatedAt = LocalDateTime.now();
    }
}