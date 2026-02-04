package com.example.iot.repository;

import com.example.iot.domain.Joint;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface JointRepository extends JpaRepository<Joint, String> {
}
