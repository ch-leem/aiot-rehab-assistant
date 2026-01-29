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
                new Fail("F_SH_FLEX", "어깨 외전 각도 미달", "어깨를 충분히 들어 올리지 못했습니다."),
                new Fail("F_EL_EXT", "팔꿈치 신전 불량", "운동 중 팔꿈치가 과하게 굽혀졌습니다."),
                new Fail("F_TR_TILT", "상체 기울기 불안정", "상체가 앞뒤로 과하게 흔들렸습니다."),
                new Fail("F_SH_HOR", "어깨 수평 불균형", "양쪽 어깨의 수평이 유지되지 않았습니다."),
                new Fail("F_ACCEL", "수행 속도 급격", "운동 속도가 일정하지 않고 너무 급합니다."),
                new Fail("F_PR_LOAD", "마비측 압력 부족", "마비측 다리에 체중을 충분히 싣지 못했습니다."),
                new Fail("F_PL_HOR", "골반 수평 편차", "골반의 수평이 무너져 자세가 불안정합니다."),
                new Fail("F_ANK_STB", "발목 흔들림 심함", "비마비측 발목이 흔들려 중심을 잡지 못했습니다."),
                new Fail("F_ELSE", "기타 실패", "전반적인 점수 미달로 실패하였습니다.")
        ));
    }
}