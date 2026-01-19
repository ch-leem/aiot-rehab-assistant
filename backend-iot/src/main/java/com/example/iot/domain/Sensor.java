package com.example.iot.domain;

import jakarta.persistence.*;

@Entity
@Table(name = "sensor")
public class Sensor {
    @Id
    @Column(name = "sensor_id", length = 20)
    private String id;

    @Column(name = "sensor_name", nullable = false, length = 50)
    private String name;

    @Column(name = "input_unit", length = 20)
    private String inputUnit;

    protected Sensor() {}

    public Sensor(String id, String name, String inputUnit) {
        this.id = id;
        this.name = name;
        this.inputUnit = inputUnit;
    }

    public String getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public String getInputUnit() {
        return inputUnit;
    }
}
