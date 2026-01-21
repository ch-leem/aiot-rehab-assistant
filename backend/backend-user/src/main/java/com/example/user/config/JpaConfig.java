package com.example.user.config;

import org.springframework.boot.autoconfigure.domain.EntityScan;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;

@Configuration
@EntityScan(basePackages = "com.example.iot.domain")
@EnableJpaRepositories(basePackages = "com.example.iot.repository")
public class JpaConfig {
}