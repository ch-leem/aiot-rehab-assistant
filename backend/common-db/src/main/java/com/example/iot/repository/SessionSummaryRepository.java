package com.example.iot.repository;

import com.example.iot.domain.SessionSummary;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface SessionSummaryRepository extends JpaRepository<SessionSummary, Long> {

    /**
     * 특정 환자의 가장 최근 세션 요약 정보를 조회합니다.
     * flow: SessionSummary -> Sequence -> Patient (id 기준)
     */
    Optional<SessionSummary> findFirstBySequence_Patient_IdOrderByIdDesc(Long patientId);
}