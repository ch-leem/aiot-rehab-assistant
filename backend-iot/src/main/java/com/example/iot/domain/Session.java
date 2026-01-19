package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import java.time.LocalDateTime;

@Entity
@Table(name = "session")
@Getter @Setter
public class Session {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "session_id")
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "sequence_id")
    private Sequence sequence;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "exercise_id")
    private Exercise exercise;

    private String goal;
    private LocalDateTime startedAt;
    private LocalDateTime endedAt;

    protected Session() {}

    public Session(Sequence sequence, Exercise exercise, String goal) {
        this.sequence = sequence;
        this.exercise = exercise;
        this.goal = goal;
        this.startedAt = LocalDateTime.now();
    }
}