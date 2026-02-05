package com.example.user.controller;

import com.example.iot.domain.Fail;
import com.example.iot.domain.Try;
import com.example.iot.repository.FailRepository;
import com.example.iot.repository.TryRepository;
import com.example.user.dto.TryFailDumpResponse;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.RestTemplate;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequiredArgsConstructor
@RequestMapping("/tries")
public class TryDebugController {

    private final RestTemplate restTemplate;
    private final TryRepository tryRepository;

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

//    @GetMapping(value = "/{tryId}/fail-log-file", produces = "application/x-ndjson")
//    public ResponseEntity<byte[]> getFailLogAsNdjson(@PathVariable Long tryId) {
//        String url = "http://iot-api:8080/tries/" + tryId + "/fail-log-file";
//
////        ResponseEntity<byte[]> resp = restTemplate.exchange(url, HttpMethod.GET, null, byte[].class);
////
////        HttpHeaders headers = new HttpHeaders();
////        headers.setContentType(MediaType.parseMediaType("application/x-ndjson; charset=utf-8"));
////        return new ResponseEntity<>(resp.getBody(), headers, resp.getStatusCode());
//
//        try {
//            // IoT 서버로 요청 보냄
//            ResponseEntity<byte[]> resp = restTemplate.exchange(url, HttpMethod.GET, null, byte[].class);
//
//            HttpHeaders headers = new HttpHeaders();
//            headers.setContentType(MediaType.parseMediaType("application/x-ndjson; charset=utf-8"));
//
//            return new ResponseEntity<>(resp.getBody(), headers, resp.getStatusCode());
//
//        } catch (HttpStatusCodeException e) {
//            // [핵심] iot-api 서버가 404나 400 등을 응답하면 그 상태 그대로 클라이언트에게 전달
//            log.warn("[PROXY ERROR] iot-api 서버 응답 오류 - Try ID: {}, Status: {}", tryId, e.getStatusCode());
//
//            return ResponseEntity.status(e.getStatusCode())
//                    .body(e.getResponseBodyAsByteArray());
//
//        } catch (Exception e) {
//            // 네트워크 연결 실패 등 기타 예외 발생 시
//            log.error("[PROXY FATAL] 서버 연결 실패 - Try ID: {}", tryId, e);
//
//            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
//                    .body(("Internal Proxy Error: " + e.getMessage()).getBytes());
//        }
//    }

//    @GetMapping(value = "/{tryId}/fail-log-file", produces = MediaType.APPLICATION_JSON_VALUE)
//    public ResponseEntity<?> getFailLogWrapped(@PathVariable Long tryId) {
//        String url = "http://iot-api:8080/tries/" + tryId + "/fail-log-file";
//
//        try {
//            ResponseEntity<String> resp = restTemplate.exchange(url, HttpMethod.GET, null, String.class);
//
//            // NDJSON -> frames[]
//            ObjectMapper om = new ObjectMapper();
//            List<JsonNode> frames = new ArrayList<>();
//
//            String body = resp.getBody();
//            if (body != null && !body.isBlank()) {
//                for (String line : body.split("\n")) {
//                    if (line.isBlank()) continue;
//                    frames.add(om.readTree(line)); // line이 프레임 1개 JSON이라고 가정
//                }
//            }
//
//
//            // fail_id는 “어디서 가져오냐”가 중요함:
//            // 1) tryId로 Fail을 조회해서 얻거나(추천)
//            // 2) 프레임 JSON 안에 fail_id가 이미 있거나
//            // 여기선 예시로 DB에서 조회한다고 가정:
//            Try t = tryRepository.findById(tryId)
//                    .orElseThrow(() -> new IllegalArgumentException("Try가 존재하지 않습니다. id=" + tryId));
//
//            Fail fail = t.getFail();
//
//            ObjectNode root = om.createObjectNode();
//            root.put("fail_id", fail.getId());
//
//            ObjectNode data = om.createObjectNode();
//            ArrayNode framesArr = om.createArrayNode();
//            frames.forEach(framesArr::add);
//
//            data.set("frames", framesArr);
//            root.set("data", data);
//
//            return ResponseEntity.ok(root);
//
//        } catch (HttpStatusCodeException e) {
//            // iot-api가 404/400 준 거 그대로 전달
//            return ResponseEntity.status(e.getStatusCode())
//                    .contentType(MediaType.TEXT_PLAIN)
//                    .body(e.getResponseBodyAsString());
//
//        } catch (Exception e) {
//            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
//                    .contentType(MediaType.TEXT_PLAIN)
//                    .body("Internal Proxy Error: " + e.getMessage());
//        }
//    }

    @GetMapping(value = "/{tryId}/fail-log-file", produces = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<?> getFailLogWrapped(@PathVariable Long tryId) {
        String url = "http://iot-api:8080/tries/" + tryId + "/fail-log-file";

        ObjectMapper om = new ObjectMapper();

        try {
            ResponseEntity<String> resp = restTemplate.exchange(url, HttpMethod.GET, null, String.class);

            String body = resp.getBody();
            if (body == null) body = "";

            // ✅ 1) fail_id 만들기 (Try -> Fail)
            Try t = tryRepository.findById(tryId)
                    .orElseThrow(() -> new IllegalArgumentException("Try가 존재하지 않습니다. id=" + tryId));

            Fail fail = t.getFail();
            String failId = (fail != null ? fail.getId() :  String.valueOf(tryId) ); // fail이 null이면 tryId라도 넣어줌(프론트 보호)

            ArrayNode framesArr = om.createArrayNode();

            String trimmed = body.trim();
            if (!trimmed.isEmpty()) {
                char first = trimmed.charAt(0);

                if (first == '{') {
                    // CASE A) "일반 JSON" 이라면
                    JsonNode rootFromIot = om.readTree(trimmed);

                    // 1) 혹시 iot-api가 이미 { data: { frames: [...] } } 형태로 주는 경우
                    JsonNode framesNode = rootFromIot.at("/data/frames");
                    if (framesNode.isArray()) {
                        framesArr.addAll((ArrayNode) framesNode);
                    } else if (rootFromIot.has("frames") && rootFromIot.get("frames").isArray()) {
                        // 2) { frames: [...] } 형태
                        framesArr.addAll((ArrayNode) rootFromIot.get("frames"));
                    } else {
                        // 3) 그냥 객체 1개만 주면 frames[0]로 넣기
                        framesArr.add(rootFromIot);
                    }

                } else if (first == '[') {
                    // CASE B) 최상위가 배열 JSON
                    JsonNode arr = om.readTree(trimmed);
                    if (arr.isArray()) framesArr.addAll((ArrayNode) arr);

                } else {
                    // CASE C) NDJSON / JSONL (한 줄에 JSON 하나)
                    for (String line : body.split("\\R")) { // \n, \r\n 모두 대응
                        String l = line.trim();
                        if (l.isEmpty()) continue;
                        framesArr.add(om.readTree(l));
                    }
                }
            }

            // ✅ 3) 프론트가 기대하는 최종 래핑 JSON 만들기
            ObjectNode root = om.createObjectNode();
            root.put("fail_id", failId);

            ObjectNode data = om.createObjectNode();
            data.set("frames", framesArr);
            root.set("data", data);

            return ResponseEntity.ok()
                    .contentType(MediaType.APPLICATION_JSON)
                    .cacheControl(CacheControl.noCache())
                    .body(root);

        } catch (HttpStatusCodeException e) {
            // iot-api가 4xx/5xx 주면 그대로 전달하되, 프론트 파싱 깨질까봐 JSON 에러로 내려주는 게 더 안전
            ObjectNode err = om.createObjectNode();
            err.put("error", "IOT_API_ERROR");
            err.put("status", e.getRawStatusCode());
            err.put("message", safeTrunc(e.getResponseBodyAsString(), 2000));
            return ResponseEntity.status(e.getStatusCode())
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(err);

        } catch (Exception e) {
            ObjectNode err = om.createObjectNode();
            err.put("error", "PROXY_INTERNAL_ERROR");
            err.put("message", safeTrunc(e.getMessage(), 2000));
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(err);
        }
    }

    private String safeTrunc(String s, int max) {
        if (s == null) return "";
        if (s.length() <= max) return s;
        return s.substring(0, max) + "...";
    }

}
