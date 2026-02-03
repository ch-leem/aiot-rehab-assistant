package com.example.iot.repository;

import com.example.iot.domain.Try;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface TryRepository extends JpaRepository<Try, Long> {

    List<Try> findBySessionId(Long sessionId);

    int countBySessionId(Long sessionId);

}
