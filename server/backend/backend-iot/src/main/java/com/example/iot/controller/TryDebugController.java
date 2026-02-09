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

//    @GetMapping("/{tryId}/fail-log-file")
//    public ResponseEntity<Resource> downloadFailLogFile(@PathVariable Long tryId) throws Exception {
//
//        Path file = dumpService.findLatestDumpFile(tryId); // 디스크에서 최신 파일 찾기
//        Resource resource = new FileSystemResource(file.toFile());
//
//        return ResponseEntity.ok()
//                .contentType(MediaType.APPLICATION_OCTET_STREAM)
//                .body(resource);
//    }

    @GetMapping(value="/{tryId}/fail-log-file", produces = "application/x-ndjson")
    public ResponseEntity<Resource> downloadFailLogFile(@PathVariable Long tryId) throws Exception {

        Path file = dumpService.findLatestDumpFile(tryId); // 디스크에서 최신 파일 찾기
        Resource resource = new FileSystemResource(file.toFile());

        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType("application/x-ndjson"))
                .body(resource);
    }

}
