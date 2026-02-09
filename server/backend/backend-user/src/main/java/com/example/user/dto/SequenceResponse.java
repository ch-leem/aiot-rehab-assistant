package com.example.user.dto;

import com.example.iot.domain.Sequence;
import lombok.Builder;
import lombok.Getter;

import java.time.LocalDateTime;

@Getter
@Builder
public class SequenceResponse {
    private Long sequenceId;
    private LocalDateTime startedAt;
    private LocalDateTime endedAt;
    private String feedback;

    public static SequenceResponse from(Sequence sequence) {
        return SequenceResponse.builder()
                .sequenceId(sequence.getId())
                .startedAt(sequence.getStartedAt())
                .endedAt(sequence.getEndedAt())
                .feedback(sequence.getFeedback())
                .build();
    }
}