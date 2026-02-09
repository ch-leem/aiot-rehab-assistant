package com.example.iot.dto.response;

import java.time.LocalDateTime;

public record SessionFinishResponse(
        Long sessionId,
       //Long sequenceId,
        LocalDateTime sessionEndedAt
       // LocalDateTime sequenceEndedAt
) {}