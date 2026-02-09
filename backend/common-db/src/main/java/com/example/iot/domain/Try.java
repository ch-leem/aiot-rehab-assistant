package com.example.iot.domain;

import com.example.iot.domain.constant.TryResult;
import jakarta.persistence.*;
import lombok.*;
import lombok.extern.slf4j.Slf4j;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Slf4j
@Entity
@Table(name = "`try`" )
@Getter @Setter
@Builder
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
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
    private Double totalScore;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "fail_id")
    private Fail fail;

    @Builder.Default
    @OneToMany(mappedBy = "exerciseTry", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<TryGoalResult> goalResults = new ArrayList<>();

    @Column(name = "started_at", nullable = false)
    private LocalDateTime startedAt;

    @Column(name = "ended_at")
    private LocalDateTime endedAt;

    public Try(Session session) {
        this.session = session;
        this.startedAt = LocalDateTime.now();
    }

    /**
     * 편의 메서드: 상세 결과를 추가하고 종합 점수를 갱신합니다.
     */
    public void addGoalResult(TryGoalResult goalResult) {
        this.goalResults.add(goalResult);
        goalResult.setExerciseTry(this);

        // 새로운 결과가 추가될 때마다 평균 점수를 다시 계산합니다.
        this.totalScore = calculateAverageScore();
    }

    /**
     * 모든 목표 달성률의 단순 산술 평균 계산
     */
    private Double calculateAverageScore() {
        if (this.goalResults == null || this.goalResults.isEmpty()) {
            return 0.0;
        }
        for(TryGoalResult temp : goalResults){
            log.info("객체 내용 확인1 {}", temp.getExerciseGoal());
            log.info("객체 내용 확인2 {}", temp.getMeasuredValue());
        }

        return this.goalResults.stream()
                .mapToDouble(TryGoalResult::getAchievementRate)
                .average()
                .orElse(0.0);
    }

    @PrePersist
    public void prePersist() {
        if (this.startedAt == null) {
            this.startedAt = LocalDateTime.now();
        }
    }
}