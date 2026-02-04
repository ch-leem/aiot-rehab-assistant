package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.*;
import java.util.List;

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

    // Sequence를 통해 요약 리스트에 접근할 수 있도록 일관성 유지
    @OneToMany(mappedBy = "sequence", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<SessionSummary> sessionSummaries;
}