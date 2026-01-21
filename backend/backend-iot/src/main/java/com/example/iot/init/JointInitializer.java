package com.example.iot.init;

import com.example.iot.domain.Joint;
import com.example.iot.repository.JointRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class JointInitializer implements CommandLineRunner {

    private final JointRepository jointRepository;

    @Override
    public void run(String... args) {
        if (jointRepository.count() == 0) {
            jointRepository.save(new Joint("1", "Shoulder"));
        }
    }
}