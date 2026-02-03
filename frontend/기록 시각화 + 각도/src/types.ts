// types.ts
export type Joint = { x: number; y: number; z: number; conf: number };

export type Frame = {
  frame_idx: number;
  ts: { video_ms: number; host_ms: number };
  position: {
    left: Record<string, Joint>;
    right: Record<string, Joint>;
    mid: Record<string, Joint>;
  };
  deg: {
    left: Record<string, number>;
    right: Record<string, number>;
    mid: Record<string, number>;
  };
  sensor: { strength: number; power: number };
};
