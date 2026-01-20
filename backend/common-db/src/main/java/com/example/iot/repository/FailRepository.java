package com.example.iot.repository;

import com.example.iot.domain.Fail;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface FailRepository extends JpaRepository<Fail, Long> {
}
