package com.example.iot.domain;

import jakarta.persistence.*;

@Entity
@Table(name = "sensormaster")
public class SensorMaster {
    @Id
    @Column(name = "sensor_id", length = 20)
    private String id;

    @Column(name = "sensor_name", nullable = false, length = 50)
    private String name;

    @Column(name = "input_unit", length = 20)
    private String inputUnit;

    protected SensorMaster() {}

    public SensorMaster(String id, String name, String inputUnit) {
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
