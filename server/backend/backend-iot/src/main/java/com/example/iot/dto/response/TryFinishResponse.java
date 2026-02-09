package com.example.iot.dto.response;

public record TryFinishResponse(
        Long tryId,
        Double totalScore,    // 이번 시도의 종합 산술 평균 점수
        String resultStatus,  // SUCCESS, FAIL 등// 시연 시 출력할 피드백 메시지
        String failName,     // 실패 시 이유 (성공 시 null 또는 빈 문자열)
        String failId          // 실패 Id
) {}