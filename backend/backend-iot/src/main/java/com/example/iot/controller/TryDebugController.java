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

    @GetMapping("/{tryId}/fail-log")
    public ResponseEntity<Resource> downloadFailLog(
            @PathVariable Long tryId,
            @RequestParam(defaultValue = "true") boolean deleteAfter
    ) throws Exception {

        Path file = dumpService.dumpRawAsJsonl(tryId, deleteAfter);

        Resource resource = new FileSystemResource(file.toFile());

        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        "attachment; filename=\"" + file.getFileName() + "\"")
                .contentType(MediaType.APPLICATION_OCTET_STREAM)
                .body(resource);
    }
}
