package com.example.iot.init;

import com.example.iot.domain.Sensor;
import com.example.iot.repository.SensorRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
@RequiredArgsConstructor
public class SensorInitializer implements CommandLineRunner {

    private final SensorRepository sensorRepository;

    @Override
    public void run(String... args) {

        if(sensorRepository.count() > 0 ) return;
        // 예: new Sensor("S1", "IMU", "deg", "XYZ", "관절 각도 센서")
        List<Sensor> sensors = List.of(
                new Sensor("IMU", "deg", "kg"),
                new Sensor("EMG", "uV", "ms"),
                new Sensor("PRESSURE", "kPa", "g"),
                new Sensor("POSITION", "cm", "s")
        );

        sensorRepository.saveAll(sensors);
    }
}

