package com.example.user.service;

import com.example.iot.repository.PatientRepository;
import com.example.user.dto.PatientResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true) // 클래스 레벨에 설정하여 모든 메서드를 읽기 전용으로 최적화
public class PatientService {

    private final PatientRepository patientRepository;

    /**
     * 전체 환자 목록 조회
     */
    public List<PatientResponse> getAllPatients() {
        return patientRepository.findAll().stream()
                .map(PatientResponse::from) // 아까 만든 DTO의 static 메서드 활용
                .collect(Collectors.toList());
    }

    /**
     * 특정 환자 상세 조회
     */
    public PatientResponse getPatientById(Long id) {
        return patientRepository.findById(id)
                .map(PatientResponse::from)
                .orElseThrow(() -> new IllegalArgumentException("해당 환자를 찾을 수 없습니다. ID: " + id));
    }
}