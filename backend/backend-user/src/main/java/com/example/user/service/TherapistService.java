package com.example.user.service;

import com.example.iot.domain.Patient;
import com.example.iot.domain.PatientTherapistMapping;
import com.example.iot.domain.SessionSummary;
import com.example.iot.domain.Therapist;
import com.example.iot.domain.constant.PatientTherapistMappingStatus;
import com.example.iot.repository.PatientRepository;
import com.example.iot.repository.PatientTherapistMappingRepository;
import com.example.iot.repository.SessionSummaryRepository;
import com.example.iot.repository.TherapistRepository;
import com.example.user.dto.PatientReportResponse;
import com.example.user.dto.TherapistDashboardResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.Period;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class TherapistService {

    private final TherapistRepository therapistRepository;
    private final PatientRepository patientRepository; // 환자 상세 조회용으로 유지
    private final SessionSummaryRepository summaryRepository;
    private final PatientTherapistMappingRepository mappingRepository; // 매핑 조회용 추가

    /**
     * 치료사 대시보드 - 담당 환자 목록 조회 (매핑 테이블 기반)
     */
    public TherapistDashboardResponse getDashboard(Long therapistId, String searchName) {
        // 1. 치료사 정보 조회
        Therapist therapist = therapistRepository.findById(therapistId)
                .orElseThrow(() -> new IllegalArgumentException("치료사를 찾을 수 없습니다."));

        // 2. 매핑 테이블을 통해 환자 목록 조회
        List<PatientTherapistMapping> mappings;
        if (searchName != null && !searchName.trim().isEmpty()) {
            mappings = mappingRepository.findAllByTherapistIdAndPatientName(
                    therapistId, searchName, PatientTherapistMappingStatus.ACTIVE);
        } else {
            mappings = mappingRepository.findAllByTherapistIdAndStatus(
                    therapistId, PatientTherapistMappingStatus.ACTIVE);
        }

        // 3. 매핑 정보에서 환자 객체를 꺼내 DTO로 변환
        List<TherapistDashboardResponse.PatientListItem> patientList = mappings.stream()
                .map(mapping -> mapToListItem(mapping.getPatient()))
                .collect(Collectors.toList());

        return TherapistDashboardResponse.builder()
                .therapistId(therapist.getId())
                .therapistName(therapist.getName())
                .patients(patientList)
                .build();
    }

    /**
     * 특정 환자의 리포트 상세 데이터 조회
     */
    public PatientReportResponse getPatientReport(Long patientId) {
        Patient patient = patientRepository.findById(patientId)
                .orElseThrow(() -> new IllegalArgumentException("환자를 찾을 수 없습니다."));

        SessionSummary summary = summaryRepository.findLatestByPatientId(patientId)
                .orElse(null);

        return PatientReportResponse.builder()
                .patientId(patient.getId())
                .patientName(patient.getName())
                .inTargetRate(summary != null ? summary.getSuccessRate() : 0.0)
                .stabilityLevel(summary != null ? summary.getSummaryTag() : "데이터 없음")
                .build();
    }

    /**
     * 기존의 나이 계산 로직 및 성별 포함
     */
    private TherapistDashboardResponse.PatientListItem mapToListItem(Patient patient) {
        int age = 0;
        if (patient.getBirthDate() != null) {
            age = Period.between(patient.getBirthDate(), LocalDate.now()).getYears();
        }

        return TherapistDashboardResponse.PatientListItem.builder()
                .patientId(patient.getId())
                .name(patient.getName())
                .gender(patient.getGender() != null ? patient.getGender().name() : null)
                .age(age)
                .diseaseName(patient.getDiseaseName())
                .build();
    }
}