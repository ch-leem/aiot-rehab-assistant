package com.example.user.controller;

import com.example.iot.domain.Device;
import com.example.iot.domain.Patient;
import com.example.iot.domain.Sensor;
import com.example.iot.domain.Therapist;
import com.example.iot.repository.DeviceRepository;
import com.example.iot.repository.PatientRepository;
import com.example.iot.repository.SensorRepository;
import com.example.iot.repository.TherapistRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/test/user")
@RequiredArgsConstructor
public class UserTestController {

    private final PatientRepository patientRepository;
    private final TherapistRepository therapistRepository;
    private final DeviceRepository deviceRepository;
    private final SensorRepository sensorRepository;

    // 1. 모든 환자 목록 조회
    @GetMapping("/patients")
    public List<Patient> getAllPatients() {
        return patientRepository.findAll();
    }

    // 2. 특정 치료사 상세 조회
    @GetMapping("/therapists/{id}")
    public Therapist getTherapist(@PathVariable Long id) {
        return therapistRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("치료사를 찾을 수 없습니다."));
    }

    // 3. 모든 기기 목록 조회
    @GetMapping("/devices")
    public List<Device> getAllDevices() {
        return deviceRepository.findAll();
    }

    // 4. 모든 센서 목록 조회
    @GetMapping("/sensors")
    public List<Sensor> getAllSensors() {
        return sensorRepository.findAll();
    }
}