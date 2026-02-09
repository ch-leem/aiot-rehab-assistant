package com.example.iot.domain;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "fail")
@Getter @Setter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Fail {

    @Id
    @Column(name = "fail_id", length = 10)
    private String id;

    @Column(name = "fail_name", nullable = false, length = 50)
    private String name;

    @Column(name = "fail_description", length = 255)
    private String failDescription;

    public Fail(String id, String name, String failDescription){
        this.id = id;
        this.name = name;
        this.failDescription = failDescription;
    }

    public Fail(String id) {
        this.id = id;
    }
}