package com.example.iot.repository;

import com.example.iot.domain.Fail;
import org.springframework.data.jpa.repository.JpaRepository;

public interface FailRepository extends JpaRepository<Fail, Long> {
}
