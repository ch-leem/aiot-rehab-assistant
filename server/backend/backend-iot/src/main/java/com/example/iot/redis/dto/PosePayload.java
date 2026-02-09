package com.example.iot.redis.dto;

import lombok.Data;

import java.util.List;

@Data
public class PosePayload {
    private List<Frame> frames;

    @Data
    public static class Frame {
        private Integer frame_idx;
        private Ts ts;
        private Object position; // 너무 복잡하면 일단 Object로 받고 나중에 분해
        private Object deg;
        private Object sensor;
    }

    @Data
    public static class Ts {
        private Long video_ms;
        private Long host_ms;
    }
}