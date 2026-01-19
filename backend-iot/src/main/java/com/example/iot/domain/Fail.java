package com.example.iot.domain;

import jakarta.persistence.*;

@Entity
@Table(name = "fail")
public class Fail {
    @Id
    @Column(name = "fail_id", length = 10)
    private String id;

    @Column(name = "fail_name", nullable = false, length = 50)
    private String name;

    @Column(name = "fail_description", length = 255)
    private String description;

    protected Fail() {}

    public Fail(String id, String name, String description){
        this.id = id;
        this.name = name;
        this.description = description;
    }

    public String getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public String getDescription() {
        return description;
    }

}
