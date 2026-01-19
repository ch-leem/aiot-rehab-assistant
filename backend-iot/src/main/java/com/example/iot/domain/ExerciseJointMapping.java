package com.example.iot.domain;


import jakarta.persistence.*;

@Entity
@Table(name = "exercise_joint_mapping")
public class ExerciseJointMapping {


    @ManyToOne(fetch = FetchType.LAZY)
    @MapsId("exerciseId") // ExerciseJointId.exerciseId에 매핑
    @JoinColumn(name = "exercise_id", nullable = false)
    @Column(name = "exercise_id")
    private Long exerciseId;

    @Column(name = "joint_id")
    private Long jointId;

    @Column(name = "role")
    private int role;

    protected ExerciseJointMapping() {}

    public ExerciseJointMapping(Long exerciseId, Long jointId) {
        this.exerciseId = exerciseId;
        this.jointId = jointId;
    }


}
