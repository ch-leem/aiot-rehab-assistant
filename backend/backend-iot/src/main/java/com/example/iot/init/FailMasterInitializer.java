package com.example.iot.init;

import com.example.iot.domain.Fail;
import com.example.iot.repository.FailRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
@RequiredArgsConstructor
public class FailMasterInitializer implements CommandLineRunner {

    private final FailRepository failRepository;

    @Override
    public void run(String... args) {
        if (failRepository.count() > 0) return;

        failRepository.saveAll(List.of(
                new Fail("F1", "수동 움직임", "근활성 부족"),
                new Fail("F2", "보상 동작", "자세 붕괴"),
                new Fail("F3", "속도 오류", "반동·급가속")
        ));
    }
}