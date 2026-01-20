package com.example.user.dto;

import com.example.iot.domain.Patient; // common-db의 엔티티 임포트
import lombok.AccessLevel;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
@AllArgsConstructor(access = AccessLevel.PRIVATE) // 외부에서 생성자 직접 호출 방지
public class PatientResponse {

    private final Long id;
    private final String name;
    private final String rehabPhase;
    // 필요하다면 여기에 생년월일을 나이로 계산해서 넣을 수도 있습니다.

    /**
     * 정적 팩토리 메서드: 엔티티를 DTO로 변환하는 로직을 DTO 안에 캡슐화합니다.
     */
    public static PatientResponse from(Patient patient) {
        return PatientResponse.builder()
                .id(patient.getId())
                .name(patient.getName())
                .rehabPhase(patient.getRehabPhase()) // 엔티티 필드명에 맞게 확인 필요
                .build();
    }
}