package com.example.user;


import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class UserHealthController {

    @GetMapping("/health")
    public String health() {
        return "User OK";
    }
}