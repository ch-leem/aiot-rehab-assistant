package com.example.iot.domain;


import jakarta.persistence.*;

@Entity
@Table(
        name = "exercise_joint_mapping",
        uniqueConstraints = {
                @UniqueConstraint(name = "uk_exercise_joint", columnNames = {"exercise_id", "joint_id"})
        }
)
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
    // 예: PRIMARY, SECONDARY, STABILIZER 등

    protected ExerciseJointMapping() {
        // JPA 기본 생성자
    }

    public ExerciseJointMapping(Exercise exercise, Joint joint, String role) {
        this.exercise = exercise;
        this.joint = joint;
        this.role = role;
    }

    // ===== getters =====
    public Long getId() {
        return id;
    }

    public Exercise getExercise() {
        return exercise;
    }

    public Joint getJoint() {
        return joint;
    }

    public String getRole() {
        return role;
    }
}