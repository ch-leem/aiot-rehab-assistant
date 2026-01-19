package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Entity
@Table(
        name = "exercise_joint_mapping",
        uniqueConstraints = {
                @UniqueConstraint(name = "uk_exercise_joint", columnNames = {"exercise_id", "joint_id"})
        }
)
@Getter @Setter
public class ExerciseJointMapping {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "mapping_id")
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "exercise_id", nullable = false)
    private Exercise exercise;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "joint_id", nullable = false)
    private Joint joint;

    @Column(name = "role", nullable = false, length = 30)
    private String role;

    protected ExerciseJointMapping() {
    }

    public ExerciseJointMapping(Exercise exercise, Joint joint, String role) {
        this.exercise = exercise;
        this.joint = joint;
        this.role = role;
    }
}