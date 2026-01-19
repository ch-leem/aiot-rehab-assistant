package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Entity
@Table(name = "sensor")
@Getter @Setter
public class Sensor {

    @Id
    @Column(name = "sensor_id", length = 20)
    private String id;

    @Column(nullable = false, length = 50)
    private String name;

    @Column(length = 20)
    private String inputUnit;

    protected Sensor() {}

    public Sensor(String id, String name, String inputUnit) {
        this.id = id;
        this.name = name;
        this.inputUnit = inputUnit;
    }
}