package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "patient_rehab_report")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
public class PatientRehabReport {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "sequence_id", nullable = false)
    private Sequence sequence;

    private String overallTitle;

    @Column(columnDefinition = "TEXT")
    private String overallAssessment;

    @Column(columnDefinition = "TEXT")
    private String fullReportJson;
}