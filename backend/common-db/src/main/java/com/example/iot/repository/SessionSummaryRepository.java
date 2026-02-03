package com.example.iot.repository;

import com.example.iot.domain.SessionSummary;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface SessionSummaryRepository extends JpaRepository<SessionSummary, Long> {

    List<SessionSummary> findAllBySequenceId(Long sequenceId);

    Optional<SessionSummary> findBySequenceIdAndSession_Exercise_Id(Long sequenceId, Long exerciseId);

    /**
     * 특정 환자의 가장 최근 세션 요약을 가져오는 쿼리 (에러 해결용)
     */
    @Query("""
        select ss from SessionSummary ss 
        where ss.sequence.patient.id = :patientId 
        order by ss.id desc 
        limit 1
    """)
    Optional<SessionSummary> findLatestByPatientId(@Param("patientId") Long patientId);
}