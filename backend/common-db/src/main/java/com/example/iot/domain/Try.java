package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import java.time.LocalDateTime;

// 결과 구분을 위한 Enum
public enum TryResult {
    SUCCESS, FAIL
}

@Entity
@Table(name = "try")
@Getter @Setter
public class Try {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "try_id")
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "session_id", nullable = false)
    private Session session;

    // 추가: 성공/실패 여부를 담는 Enum 컬럼
    @Enumerated(EnumType.STRING)
    @Column(name = "result", length = 20)
    private TryResult result;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "fail_id")
    private Fail fail; // 실패 원인 등을 담은 별도 엔티티로 추정

    private String goalVision;

    private String goalSensor;

    private LocalDateTime startedAt;

    private LocalDateTime endedAt;

    protected Try() {}

    // 기존 생성자에 result 추가 가능 (선택)
    public Try(Session session) {
        this.session = session;
        this.startedAt = LocalDateTime.now();
    }

    @PrePersist
    public void prePersist() {
        if (startedAt == null) startedAt = LocalDateTime.now();
    }
}