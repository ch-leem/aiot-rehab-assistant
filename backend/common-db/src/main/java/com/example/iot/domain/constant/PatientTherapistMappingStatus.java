package com.example.iot.domain.constant;

import lombok.Getter;
import lombok.RequiredArgsConstructor;

@Getter
@RequiredArgsConstructor
public enum PatientTherapistMappingStatus {
    ACTIVE("활성", "현재 담당 중인 상태"),
    TERMINATED("종료", "치료가 종료되었거나 담당이 바뀐 상태"),
    PENDING("대기", "배정 승인 대기 중인 상태");

    private final String label;
    private final String description;
}