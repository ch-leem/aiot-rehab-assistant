package com.example.iot.dto.response;

import java.time.LocalDateTime;

public record TryStartResponse(
        Long tryId,
        LocalDateTime startedAt
) {}