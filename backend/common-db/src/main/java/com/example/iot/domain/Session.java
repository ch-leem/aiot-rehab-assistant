package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "session")
@Getter @Setter
public class Session {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "session_id")
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "sequence_id", nullable = false)
    private Sequence sequence;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "exercise_id", nullable = false)
    private Exercise exercise;

    private String goal = "0";

    @Column(name = "total_tries")
    private int totalTries = 0; // 전체 시도 횟수

    @Column(name = "success_tries")
    private int successTries = 0; // 성공 시도 횟수

    private LocalDateTime startedAt;

    private LocalDateTime endedAt;

    @OneToMany(mappedBy = "session", cascade = CascadeType.ALL)
    private List<Try> tries = new ArrayList<>();

    protected Session() {}

    public Session(Sequence sequence, Exercise exercise) {
        this.sequence = sequence;
        this.exercise = exercise;
        this.startedAt = LocalDateTime.now();
        this.totalTries = 0;
        this.successTries = 0;
    }

    @PrePersist
    public void prePersist() {
        if (startedAt == null) startedAt = LocalDateTime.now();
    }
    public void addSuccessTries() {
        this.successTries++;
    }
}