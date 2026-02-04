package com.example.iot.repository;

import com.example.iot.domain.PatientRehabReport;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface PatientRehabReportRepository extends JpaRepository<PatientRehabReport, Long> {

    /**
     * [리포트용 추가] 특정 세션에 저장된 AI의 정밀 분석 소견 조회
     */
    @Query("SELECT r.aiNote FROM PatientRehabReport r WHERE r.sessionId = :sessionId")
    Optional<String> findAiNoteBySessionId(@Param("sessionId") Long sessionId);

    /**
     * [리포트용 추가] 특정 시퀀스에 대한 전체 요약 리포트 존재 여부 확인 등
     */
    Optional<PatientRehabReport> findBySequenceId(Long sequenceId);
}