package com.example.iot.repository;

import com.example.iot.domain.PatientTherapistMapping;
import com.example.iot.domain.constant.PatientTherapistMappingStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import java.util.List;

public interface PatientTherapistMappingRepository extends JpaRepository<PatientTherapistMapping, Long> {

    // 치료사 ID로 활성 상태인 환자 목록(매핑) 조회
    @Query("SELECT m FROM PatientTherapistMapping m JOIN FETCH m.patient " +
            "WHERE m.therapist.id = :therapistId AND m.status = :status")
    List<PatientTherapistMapping> findAllByTherapistIdAndStatus(
            @Param("therapistId") Long therapistId,
            @Param("status") PatientTherapistMappingStatus status);

    // 이름 검색 포함
    @Query("SELECT m FROM PatientTherapistMapping m JOIN FETCH m.patient p " +
            "WHERE m.therapist.id = :therapistId " +
            "AND p.name LIKE %:name% " +
            "AND m.status = :status")
    List<PatientTherapistMapping> findAllByTherapistIdAndPatientName(
            @Param("therapistId") Long therapistId,
            @Param("name") String name,
            @Param("status") PatientTherapistMappingStatus status);
}