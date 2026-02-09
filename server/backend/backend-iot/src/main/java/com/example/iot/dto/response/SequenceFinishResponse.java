package com.example.iot.dto.response;

import java.time.LocalDateTime;

public record SequenceFinishResponse(
        Long sequenceId,
        LocalDateTime endedAt
) {}