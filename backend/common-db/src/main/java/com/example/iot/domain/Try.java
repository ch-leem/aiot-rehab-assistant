package com.example.iot.domain;

import com.example.iot.domain.constant.TryResult;
import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "try")
@Getter @Setter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Try {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "try_id")
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "session_id", nullable = false)
    private Session session;

    @Enumerated(EnumType.STRING)
    @Column(name = "result", length = 20)
    private TryResult result;

    @Column(name = "total_score")
    private Double totalScore; // 이번 시도의 종합 점수 (0~100)

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "fail_id")
    private Fail fail;

    @OneToMany(mappedBy = "try", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<TryGoalResult> goalResults = new ArrayList<>();

    @Column(name = "started_at", nullable = false)
    private LocalDateTime startedAt;

    @Column(name = "ended_at")
    private LocalDateTime endedAt;

    // 생성자 유지 및 초기화 로직
    public Try(Session session) {
        this.session = session;
        this.startedAt = LocalDateTime.now();
    }

    /**
     * 편의 메서드: 상세 결과를 추가할 때 양방향 관계를 설정합니다.
     */
    // Try.java 파일 내부

    public void addGoalResult(TryGoalResult goalResult) {
        this.goalResults.add(goalResult);
        goalResult.setExerciseTry(this);
    }

    @PrePersist
    public void prePersist() {
        if (this.startedAt == null) {
            this.startedAt = LocalDateTime.now();
        }
    }
}