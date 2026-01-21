package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Entity
@Table(name = "fail")
@Getter @Setter
public class Fail {

    @Id
    @Column(name = "fail_id", length = 10)
    private String id;

    @Column(nullable = false, length = 50)
    private String name;

    @Column(length = 255)
    private String description;

    protected Fail() {}

    public Fail(String id, String name, String description){
        this.id = id;
        this.name = name;
        this.description = description;
    }

    public Fail(String id) {
        this.id = id;
    };
}