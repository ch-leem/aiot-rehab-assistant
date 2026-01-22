package com.example.iot.repository;

import com.example.iot.domain.Patient;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface PatientRepository extends JpaRepository<Patient, Long> {
    // 치료사 ID로 담당 환자 목록 조회
    List<Patient> findByTherapist_Id(Long therapistId);

    // 이름 검색 기능 추가
    List<Patient> findByTherapist_IdAndNameContaining(Long therapistId, String name);
}