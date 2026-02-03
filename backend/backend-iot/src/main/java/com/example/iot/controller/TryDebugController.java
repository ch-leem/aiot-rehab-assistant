package com.example.iot.controller;

import com.example.iot.service.TryRawDumpService;
import lombok.RequiredArgsConstructor;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;

import java.nio.file.Path;

@RestController
@RequiredArgsConstructor
@RequestMapping("/tries")
public class TryDebugController {

    private final TryRawDumpService dumpService;

    // ✅ Redis가 아니라, 이미 생성된 파일을 가져오기만
    @GetMapping("/{tryId}/fail-log-file")
    public ResponseEntity<Resource> downloadFailLogFile(@PathVariable Long tryId) throws Exception {

        Path file = dumpService.findLatestDumpFile(tryId); // 디스크에서 최신 파일 찾기
        Resource resource = new FileSystemResource(file.toFile());

        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        "attachment; filename=\"" + file.getFileName() + "\"")
                .contentType(MediaType.APPLICATION_OCTET_STREAM)
                .body(resource);
    }

}
