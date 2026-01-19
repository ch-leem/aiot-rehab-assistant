package com.example.iot.repository;

import com.example.iot.domain.Try;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TryRepository extends JpaRepository<Try, Long> {
}
