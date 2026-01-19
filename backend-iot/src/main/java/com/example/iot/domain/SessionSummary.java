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

    private Integer totalTrials;
    private Integer successTrials;
    private Double avgAngle;
    private Double inTargetRate;
    private Integer compensationTotal;
    private String stabilityLevel;

    protected SessionSummary() {}

    public SessionSummary(Sequence sequence) {
        this.sequence = sequence;
    }
}