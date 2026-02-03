// lib/loadNdjson.ts
import type { Frame } from "@/types";

export async function loadNdjson(file: File): Promise<Frame[]> {
  try {
    const text = await file.text();
    const lines = text.split("\n").filter(Boolean);
    const parsed = lines.map((l) => JSON.parse(l));

    // Basic validation: Check if the first item has expected fields
    if (parsed.length > 0) {
      const first = parsed[0];
      if (!("frame_idx" in first) || !("ts" in first)) {
        throw new Error("Invalid file format: Missing frame_idx or ts");
      }
    }

    return parsed as Frame[];
  } catch (error) {
    console.error("Error parsing NDJSON:", error);
    throw error;
  }
}
