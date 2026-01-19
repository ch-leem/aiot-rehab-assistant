package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Entity
@Table(name = "session_summary")
@Getter @Setter
public class SessionSummary {

    @Id
    private Long sequenceId;

    @OneToOne(fetch = FetchType.LAZY)
    @MapsId
    @JoinColumn(name = "sequence_id")
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