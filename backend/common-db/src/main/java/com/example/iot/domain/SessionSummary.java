package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "session_summary")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
public class SessionSummary {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "sequence_id", nullable = false)
    private Sequence sequence;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "session_id", nullable = false)
    private Session session;

    private Double successRate;
    private Double averageScore;

    private String summaryTag;         // STABLE, VARIABLE, UNSTABLE 등
    private String sessionTrend; // IMPROVING, STABLE, DECLINING 등

    @Column(columnDefinition = "TEXT")
    private String sessionNote; // "어깨 가동 범위는 양호하나..."

    private String trend;            // IMPROVING, STABLE 등 (이전 대비)

    @Column(columnDefinition = "TEXT")
    private String trendDescription; // "이전 세션에서 언급된..."
}