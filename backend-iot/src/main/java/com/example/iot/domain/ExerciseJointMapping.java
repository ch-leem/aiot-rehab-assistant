package com.example.iot.domain;


import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;

import java.io.Serializable;

@Entity
@Table(name = "exercise_joint_mapping")
public class Exercise_joint_mapping {
    @Column(name = "exercise_id")
    private Long exerciseId;

    @Column(name = "joint_id")
    private Long jointId;

    protected Exercise_joint_mapping() {}

    public Exercise_joint_mapping(Long exerciseId, Long jointId) {
        this.exerciseId = exerciseId;
        this.jointId = jointId;
    }

}
