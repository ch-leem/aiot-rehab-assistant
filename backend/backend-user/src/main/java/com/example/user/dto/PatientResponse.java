package com.example.user.dto;

import com.example.iot.domain.Patient;
import com.example.iot.domain.Therapist;
import lombok.AccessLevel;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
@AllArgsConstructor(access = AccessLevel.PRIVATE)
public class PatientResponse {

    private final Long id;
    private final String name;
    private final String rehabPhase;

    // [Bundle 1] 치료사 정보 (Therapist)
    private final Long therapistId;
    private final String therapistName;
    private final String therapistSpecialty; // 치료사 전공 분야 등

    // [Bundle 2] 관리 정보 (필요시 추가)
    // 현재 진행 중인 시퀀스(처방)의 ID or 이름을 포함 가능
    private final Long currentSequenceId;

    /**
     * 정적 팩토리 메서드: 엔티티들을 조합해 DTO로 변환
     */
    public static PatientResponse from(Patient patient) {
        // 치료사 정보 추출 (Null 처리 포함)
        Therapist therapist = patient.getTherapist();
        
        return PatientResponse.builder()
                .id(patient.getId())
                .name(patient.getName())
                .rehabPhase(patient.getRehabPhase())
                
                // 치료사 정보 매핑
                .therapistId(therapist != null ? therapist.getId() : null)
                .therapistName(therapist != null ? therapist.getName() : "미지정")
                // 만약 Therapist 엔티티에 specialty 필드가 있다면 추가 가능
                // .therapistSpecialty(therapist != null ? therapist.getSpecialty() : null)
                
                // 환자 엔티티에 현재 진행 중인 시퀀스 정보가 연관되어 있다면 추가
                // .currentSequenceId(patient.getCurrentSequence() != null ? patient.getCurrentSequence().getId() : null)
                .build();
    }
}