package com.example.iot.repository;

import com.example.iot.domain.Sequence;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface SequenceRepository extends JpaRepository<Sequence, Long> {

    //환자 id별로 현재 진행한 sequence정보 가져오기
    List<Sequence> findByPatient_IdOrderByStartedAtDesc(Long patientId);
}
