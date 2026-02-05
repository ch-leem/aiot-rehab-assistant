package com.example.user.controller;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.RestTemplate;
import java.nio.file.Path;

@Slf4j
@RestController
@RequiredArgsConstructor
@RequestMapping("/tries")
public class TryDebugController {

    private final RestTemplate restTemplate;

//    @GetMapping("/{tryId}/fail-log-file")
//    public ResponseEntity<byte[]> getFailLog(@PathVariable Long tryId) {
//        String url = "http://iot-api:8080/tries/" + tryId + "/fail-log-file";
//
//        ResponseEntity<byte[]> resp = restTemplate.exchange(
//                url,
//                HttpMethod.GET,
//                new HttpEntity<>(new HttpHeaders()),
//                byte[].class
//        );
//
//        HttpHeaders headers = new HttpHeaders();
//        // iot 서버가 주는 content-type을 최대한 유지
//        MediaType ct = resp.getHeaders().getContentType();
//        if (ct != null) headers.setContentType(ct);
//
//        // 파일 다운로드처럼 보이게 하고 싶으면(선택)
//        String disposition = resp.getHeaders().getFirst(HttpHeaders.CONTENT_DISPOSITION);
//        if (disposition != null) headers.set(HttpHeaders.CONTENT_DISPOSITION, disposition);
//
//        return new ResponseEntity<>(resp.getBody(), headers, resp.getStatusCode());
//    }

    @GetMapping(value = "/{tryId}/fail-log-file", produces = "application/x-ndjson")
    public ResponseEntity<byte[]> getFailLogAsNdjson(@PathVariable Long tryId) {
        String url = "http://iot-api:8080/tries/" + tryId + "/fail-log-file";

//        ResponseEntity<byte[]> resp = restTemplate.exchange(url, HttpMethod.GET, null, byte[].class);
//
//        HttpHeaders headers = new HttpHeaders();
//        headers.setContentType(MediaType.parseMediaType("application/x-ndjson; charset=utf-8"));
//        return new ResponseEntity<>(resp.getBody(), headers, resp.getStatusCode());

        try {
            // IoT 서버로 요청 보냄
            ResponseEntity<byte[]> resp = restTemplate.exchange(url, HttpMethod.GET, null, byte[].class);

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.parseMediaType("application/x-ndjson; charset=utf-8"));

            return new ResponseEntity<>(resp.getBody(), headers, resp.getStatusCode());

        } catch (HttpStatusCodeException e) {
            // [핵심] iot-api 서버가 404나 400 등을 응답하면 그 상태 그대로 클라이언트에게 전달
            log.warn("[PROXY ERROR] iot-api 서버 응답 오류 - Try ID: {}, Status: {}", tryId, e.getStatusCode());

            return ResponseEntity.status(e.getStatusCode())
                    .body(e.getResponseBodyAsByteArray());

        } catch (Exception e) {
            // 네트워크 연결 실패 등 기타 예외 발생 시
            log.error("[PROXY FATAL] 서버 연결 실패 - Try ID: {}", tryId, e);

            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(("Internal Proxy Error: " + e.getMessage()).getBytes());
        }
    }
}
