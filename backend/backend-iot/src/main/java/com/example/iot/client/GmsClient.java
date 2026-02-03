package com.example.iot.client;

import com.example.iot.dto.request.PatientRehabReportRequest;
import com.example.iot.dto.response.PatientRehabReportResponse;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class GmsClient {

    private final WebClient webClient;
    private final ObjectMapper objectMapper;

    @Value("${gms.api.key}")
    private String gmsKey;

    @Value("${gms.api.url}")
    private String gmsUrl;

    public GmsClient(WebClient.Builder webClientBuilder, ObjectMapper objectMapper) {
        this.webClient = webClientBuilder.build();
        this.objectMapper = objectMapper;
    }

    public PatientRehabReportResponse getLlmAnalysis(PatientRehabReportRequest requestDto) {
        String systemPrompt = """
            You are a clinical rehabilitation reporting assistant.
            
            Strict rules:
            - Do NOT provide medical diagnoses, treatment decisions, or prescriptions.
            - Use only observational, descriptive, and trend-based language.
            - Do NOT introduce information not supported by the input data.
            - Do NOT infer clinical intent beyond what the data directly implies.
            - Always return output strictly in valid JSON format.
            - Follow the provided output schema exactly.
            - Include no explanations outside the JSON output.
            - This report does not replace clinical judgment.
            """;
        String developerPrompt = """
            You generate concise clinical insight summaries for rehabilitation professionals.
            
            Fill each field according to its defined meaning in the output schema.
            
            Rules:
            - Base all content strictly on the input data.
            - Use observable patterns at sequence and session levels.
            - Emphasize task execution quality, stability, and safety.
            - Avoid diagnoses, prescriptions, or treatment decisions.
            - Keep all descriptions concise and suitable for quick clinical review.
            - Maintain consistent phrasing and information density across cases.
            
            """;
        String outputSchema = """
            {
              "sequenceId": number,
              "patientName": string,
              "date": string,
              "rehabPhase": string,
              "side": string,
            
              "overallSummary": {
                "title": string,
                // 이번 시퀀스를 한 문장으로 요약하는 임상적 헤드라인
                "totalExercises": number,
                // 이번 시퀀스에 포함된 운동 수
                "overallAssessment": string
                // - 시퀀스 전체 관점에서의 핵심 임상 인사이트
                // - “무엇이 유지되었고 / 무엇이 흔들렸는가”
                // - 세부 관절 나열 X, 지배적인 패턴만 O
              },
            
              "exerciseSummaries": [
                {
                  "exerciseName": string,
                  "performance": {
                    "successRate": number,
                    // 과제 수행 가능성의 요약 지표
                    "averageScore": number
                    // 전반적 수행 수준의 참고 지표 (판단의 기준은 아님)
                  },
            
                  "summaryTag": "STABLE | VARIABLE | UNSTABLE",
                  // - STABLE: 주요/보조 관절 모두 일관
                  // - VARIABLE: 주요 과제는 가능하나 안정성 변동
                  // - UNSTABLE: 수행 자체 또는 안전성에 반복적 문제
            
                  "withinSessionTrend": "IMPROVING | STABLE | DECLINING",
                  // - 단일 세션 내 try 진행에 따른 변화
                  // - 이전 세션과는 무관
            
                  "sessionNote": string,
                  // - 이 운동 하나를 대표하는 한 줄 임상 메모
                  // - 주요 관절 + 안정성 관절을 자연스럽게 포함
            
                  "keyObservations": string[],
                  // - 최대 3개
                  // - 관절/분절 단위의 핵심 관찰
                  // - 주 동작 관절, 안정성/보상 관절, 둘의 상호 영향
            
                  "comparisonToPrevious": {
                    "used": boolean,
                    "trend": "IMPROVING | STABLE | DECLINING | NOT_APPLICABLE",
                    // 이전 세션 대비 변화 방향 (세션 간)
            
                    "trendDescription": string | null
                    // - “무엇이 나아졌는지 / 무엇이 여전히 남아있는지”
                    // - 수치 나열 X, 변화 포인트만 O
                  }
                }
              ],
            
              "riskSignals": string[],
              // - 안전/모니터링 관점에서 놓치면 안 되는 신호
              // - 실패 반복, 후반부 붕괴, 특정 관절 급격 악화 등
            
              "nextFocus": string[]
              // - 다음 세션에서 특히 봐야 할 포인트
              // - 치료 지시X, 관찰 포커스O
            }
            
            """;

        String userPrompt = String.format(
                """
                Generate a rehabilitation progress report for medical professionals using the following input data.
                
                ### Input (SequenceReportRequest):
                ```json
                %s
                ```
                
                ### Output Schema:
                ```json
                %s
                ```
                """,
                serialize(requestDto), outputSchema
        );

        Map<String, Object> payload = Map.of(
                "model", "gpt-4o", // GMS에서 지원하는 모델명으로 기입
                "temperature", 0.2,
                "messages", List.of(
                        Map.of("role", "system", "content", systemPrompt),
                        Map.of("role", "developer", "content", developerPrompt),
                        Map.of("role", "user", "content", userPrompt)
                )
        );

        String responseBody = webClient.post()
                .uri(gmsUrl)
                .header("Authorization", "Bearer " + gmsKey)
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(payload)
                .retrieve()
                .bodyToMono(String.class)
                .block();

        return parseResponse(responseBody);
    }

    private PatientRehabReportResponse parseResponse(String responseBody) {
        try {
            var root = objectMapper.readTree(responseBody);
            String content = root.path("choices").get(0).path("message").path("content").asText();
            content = content.replaceAll("```json|```", "").trim();
            return objectMapper.readValue(content, PatientRehabReportResponse.class);
        } catch (Exception e) {
            log.error("LLM 파싱 에러: {}", e.getMessage());
            throw new RuntimeException("AI 분석 결과 처리 실패");
        }
    }

    private String serialize(Object obj) {
        try { return objectMapper.writeValueAsString(obj); }
        catch (JsonProcessingException e) { return "{}"; }
    }
}