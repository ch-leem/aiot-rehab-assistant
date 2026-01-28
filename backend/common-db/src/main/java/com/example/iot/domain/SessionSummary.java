package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Entity
@Table(name = "session_summary")
@Getter @Setter
public class SessionSummary {

    @Id
    @Column(name = "sequence_id")
    private Long id;

    @OneToOne(fetch = FetchType.LAZY)
    @MapsId
    @JoinColumn(name = "sequence_id", nullable = false)
    private Sequence sequence;

    @Column(name = "total_trials")
    private Long totalTrials; // int8 대응

    @Column(name = "success_trials")
    private Long successTrials; // int8 대응

    @Column(name = "avg_angle")
    private Double avgAngle;

    @Column(name = "in_target_rate")
    private Double inTargetRate;

    @Column(name = "compensation_total")
    private Long compensationTotal; // int8 대응

    @Column(name = "stability_level")
    private String stabilityLevel;

    protected SessionSummary() {}

    public SessionSummary(Sequence sequence) {
        this.sequence = sequence;
    }
}