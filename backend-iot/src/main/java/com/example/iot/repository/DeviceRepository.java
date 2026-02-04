package com.example.iot.repository;

import com.example.iot.domain.Device;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface DeviceRepository extends JpaRepository<Device, String> {

    //현재 사용중이지 않은 device 조회
    List<Device> findByOccupiedFalse();
    //현재 사용 중인 device 조회
    List<Device> findByOccupiedTrue();

}
