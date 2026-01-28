package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import java.time.LocalDateTime;

@Entity
@Table(name = "patient_device_mapping")
@Getter @Setter
public class PatientDeviceMapping {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "mapping_id")
    private Long id;

    // 환자 엔티티와 연관관계 (FK: int8)
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "patient_id", nullable = false)
    private Patient patient;

    // 기기 엔티티와 연관관계 (FK: varchar(255))
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "device_id", nullable = false)
    private Device device;

    @Column(name = "assigned_at", nullable = false, updatable = false)
    private LocalDateTime assignedAt;

    public PatientDeviceMapping() {}

    public PatientDeviceMapping(Patient patient, Device device) {
        this.patient = patient;
        this.device = device;
        this.assignedAt = LocalDateTime.now();
    }

    @PrePersist
    public void prePersist() {
        if (assignedAt == null) {
            assignedAt = LocalDateTime.now();
        }
    }
}