package com.example.user.controller;


import lombok.RequiredArgsConstructor;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import java.nio.file.Path;

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

//        ResponseEntity<byte[]> resp = restTemplate.exchange(
//                url,
//                HttpMethod.GET,
//                new HttpEntity<>(new HttpHeaders()),
//                byte[].class
//        );
//
//        HttpHeaders headers = new HttpHeaders();
//
//        // content-type 유지하되, 없거나 octet-stream이면 NDJSON로 교체
//        MediaType ct = resp.getHeaders().getContentType();
//        if (ct == null || MediaType.APPLICATION_OCTET_STREAM.equalsTypeAndSubtype(ct)) {
//            headers.setContentType(MediaType.parseMediaType("application/x-ndjson; charset=utf-8"));
//        } else {
//            headers.setContentType(ct);
//        }
//
//        // ✅ 다운로드 강제 헤더 제거(핵심)
//        // Content-Disposition 전달하지 않음
//
//        // (선택) 캐시 방지
//        headers.setCacheControl(CacheControl.noStore());
//
//        return new ResponseEntity<>(resp.getBody(), headers, resp.getStatusCode());
//
        ResponseEntity<byte[]> resp = restTemplate.exchange(url, HttpMethod.GET, null, byte[].class);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.parseMediaType("application/x-ndjson; charset=utf-8"));
        return new ResponseEntity<>(resp.getBody(), headers, resp.getStatusCode());
    }

}
