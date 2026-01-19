package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import java.time.LocalDateTime;

@Entity
@Table(name = "device")
@Getter @Setter
public class Device {

    @Id
    @Column(name = "device_id")
    private String id; // 수동 입력 PK

    private String model;
    private String firmwareVersion;
    private boolean occupied;

    @Column(name = "registered_at", nullable = false, updatable = false)
    private LocalDateTime registeredAt;

    protected Device() {}

    public Device(String id, String model, String firmwareVersion) {
        this.id = id;
        this.model = model;
        this.firmwareVersion = firmwareVersion;
        this.occupied = false;
        this.registeredAt = LocalDateTime.now();
    }
}