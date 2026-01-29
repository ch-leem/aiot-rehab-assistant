package com.example.iot.repository;

import com.example.iot.domain.SessionSummary;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SessionSummaryRepository extends JpaRepository<SessionSummary, Long> {
}
