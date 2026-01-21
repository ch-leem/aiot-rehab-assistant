package com.example.iot.init;

import com.example.iot.domain.Device;
import com.example.iot.repository.DeviceRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
@RequiredArgsConstructor
public class DeviceInitializer implements CommandLineRunner {

    private final DeviceRepository deviceRepository;

    @Override
    public void run(String... args) {

        if(deviceRepository.count() > 0) return;
       List<Device> devices = List.of(
                new Device("DEV-001", "Jetson Orin Nano", "0.1.0"),
                new Device("DEV-002", "Raspberry Pi 5", "0.1.0")
        );

        deviceRepository.saveAll(devices);
    }
}