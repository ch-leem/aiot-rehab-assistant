package com.example.user.service;

import com.example.iot.domain.ExercisePatientMapping;
import com.example.iot.repository.ExercisePatientMappingRepository;
import com.example.user.dto.PatientExerciseConfigResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class ExerciseService {

    private final ExercisePatientMappingRepository mappingRepository;

    /**
     * 특정 환자에게 할당된 맞춤형 운동 설정 리스트 조회
     */
    public List<PatientExerciseConfigResponse> getPatientExerciseConfigs(Long patientId) {
        // 현재는 전체를 가져와 필터링 (추후 리포지토리 메서드 추가 권장)
        return mappingRepository.findAll().stream()
                .filter(m -> m.getPatient().getId().equals(patientId))
                .map(PatientExerciseConfigResponse::from)
                .toList();
    }
}