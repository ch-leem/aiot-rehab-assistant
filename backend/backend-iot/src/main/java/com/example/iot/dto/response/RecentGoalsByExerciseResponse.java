package com.example.iot.dto.response;

import java.util.List;

public record RecentGoalsByExerciseResponse(
        Long patientId,
        Long currentSequenceId,
        int lookbackSequences,              // 뒤로 몇 개 시퀀스까지 뒤졌는지(디버깅용)
        List<ExerciseRecentGoalsItem> items
) {}