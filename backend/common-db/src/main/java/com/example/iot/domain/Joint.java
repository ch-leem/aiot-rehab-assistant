package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Entity
@Table(name = "joint")
@Getter @Setter
public class Joint {

    @Id
    @Column(name = "joint_id", length = 20)
    private String id;

    @Column(name = "joint_name", nullable = false, length = 50)
    private String name;

    protected Joint() {}

    public Joint(String id, String name) {
        this.id = id;
        this.name = name;
    }
}