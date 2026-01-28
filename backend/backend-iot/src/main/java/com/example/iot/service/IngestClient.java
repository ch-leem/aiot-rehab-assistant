package com.example.iot.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.Map;

@Slf4j
@Service
public class IngestClient {
    private final WebClient webClient;
    private final String ingestBaseUrl;

    public IngestClient(
            WebClient.Builder builder,
            @Value("${ingest.base-url}") String baseUrl
    ) {
        this.webClient = builder.baseUrl(baseUrl).build();
        this.ingestBaseUrl = baseUrl;
    }

    public void startTry(String tryId) {
        log.info("[INGEST] ▶ 요청 시도");
        log.info("[INGEST] baseUrl = {}", ingestBaseUrl);

        webClient.post().uri("/try/start")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(Map.of("try_id", tryId))
                .retrieve()
                .toBodilessEntity()
                .block();
    }

    public void stopTry() {
        webClient.post().uri("/try/stop")
                .retrieve()
                .toBodilessEntity()
                .block();
    }


}