package com.example.user.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;

import java.util.Map;

@Getter
@AllArgsConstructor
public class TryFailDumpResponse {
    private Long failId;   // 또는 List<Long> failIds
    private Map<String, Object> data; // {"frames": [...]}
}