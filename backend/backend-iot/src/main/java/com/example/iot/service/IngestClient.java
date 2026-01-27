package com.example.iot.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.Map;

@Service
public class IngestClient {
    private final WebClient webClient;

    public IngestClient(
            WebClient.Builder builder,
            @Value("${ingest.base-url}") String baseUrl
    ) {
        this.webClient = builder.baseUrl(baseUrl).build();
    }

    public void startTry(String tryId) {
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