package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import java.time.LocalDateTime;

@Entity
@Table(name = "try")
@Getter @Setter
public class Try {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "try_id")
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "session_id")
    private Session session;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "fail_id")
    private Fail failMaster;

    private String goalVision;
    private String goalSensor;
    private LocalDateTime startedAt;
    private LocalDateTime endedAt;

    protected Try() {}

    public Try(Session session) {
        this.session = session;
        this.startedAt = LocalDateTime.now();
    }
}