package com.example.iot;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class IotHealthController {

    @GetMapping("/health")
    public String health() {
        return "IOT OK";
    }
}
