package com.example.iot.repository;

import com.example.iot.domain.Patient;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface PatientRepository extends JpaRepository<Patient, Long> {
    // 치료사 관련 메서드는 삭제하거나 주석 처리하고, 환자 고유 기능만 남깁니다.
    // 예: 이름으로만 검색 (전체 환자 대상)
    List<Patient> findByNameContaining(String name);
}