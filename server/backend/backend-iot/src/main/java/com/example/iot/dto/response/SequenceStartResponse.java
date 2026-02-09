package com.example.iot.dto.response;

import java.util.List;

public record SequenceStartResponse(
        Long sequenceId,
        List<SessionTryResponse> sessions
) {}