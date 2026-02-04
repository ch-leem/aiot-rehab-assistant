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
     * [리포트용 추가] 특정 시퀀스에 대한 전체 요약 리포트 존재 여부 확인 등
     */
    Optional<PatientRehabReport> findBySequenceId(Long sequenceId);
}