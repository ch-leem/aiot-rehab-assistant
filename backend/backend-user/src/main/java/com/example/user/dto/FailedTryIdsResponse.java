package com.example.user.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;

import java.util.List;

@Getter
@AllArgsConstructor
public class FailedTryIdsResponse {
    private Long sessionId;
    private List<Long> failedTryIds;
    private int count;
}
