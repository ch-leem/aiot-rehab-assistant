package com.example.iot.exception;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class IotExceptionHandler {

    // 1. 서비스에서 던진 IllegalStateException 처리 ("이미 종료된 운동 시도입니다.")
    @ExceptionHandler(IllegalStateException.class)
    public ResponseEntity<String> handleIllegalState(IllegalStateException e) {
        return ResponseEntity.badRequest().body(e.getMessage()); // 400 Bad Request
    }

    // 2. 존재하지 않는 ID 조회 시 (IllegalArgumentException)
    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<String> handleIllegalArgument(IllegalArgumentException e) {
        return ResponseEntity.status(404).body(e.getMessage()); // 404 Not Found
    }

    // 3. 그 외 예상치 못한 모든 예외 처리
    @ExceptionHandler(Exception.class)
    public ResponseEntity<String> handleGeneralException(Exception e) {
        return ResponseEntity.internalServerError().body("서버 내부 오류가 발생했습니다."); // 500
    }
}