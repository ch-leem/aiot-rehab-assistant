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

    private String summaryTag;    // 예: VARIABLE, STABLE
    private String sessionTrend;  // 예: DECLINING, IMPROVING (세션 내 추세)

    @Column(columnDefinition = "TEXT")
    private String sessionNote;   // AI 세션별 소견

    private String trend;         // 이전 대비 추세 (IMPROVING 등)

    @Column(columnDefinition = "TEXT")
    private String trendDescription; // 이전 대비 상세 설명
}