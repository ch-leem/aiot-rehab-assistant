package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import java.time.LocalDateTime;

@Entity
@Getter @Setter
public class Device {
    @Id
    private String DeviceId;

    private String Model;
    private String FirmwareVersion;
    private LocalDateTime RegisteredAt = LocalDateTime.now();
    private boolean Occupied;
}