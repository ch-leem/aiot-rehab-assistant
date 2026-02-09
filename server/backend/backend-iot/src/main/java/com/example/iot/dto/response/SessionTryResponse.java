package com.example.iot.dto.response;

import java.util.List;

public record SessionTryResponse(
        Long sessionId,
        List<Long> tryIds
) {}