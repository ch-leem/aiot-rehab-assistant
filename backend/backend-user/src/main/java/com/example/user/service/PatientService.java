package com.example.user.service;

import com.example.iot.domain.Patient;
import com.example.iot.repository.PatientRepository;
import com.example.user.dto.PatientResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true) // 조회 전용이므로 성능 최적화
public class PatientService {

    private final PatientRepository patientRepository;

    public PatientResponse getPatientDetail(Long patientId) {
        Patient patient = patientRepository.findById(patientId)
                .orElseThrow(() -> new IllegalArgumentException("해당 환자를 찾을 수 없습니다. ID: " + patientId));
        
        return PatientResponse.from(patient);
    }
}