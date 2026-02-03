package com.example.iot.repository;

import com.example.iot.domain.Sequence;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface SequenceRepository extends JpaRepository<Sequence, Long> {

    //환자 id별로 현재 진행한 sequence정보 가져오기
    List<Sequence> findByPatient_IdOrderByStartedAtDesc(Long patientId);

    @Query("""
        select s
        from Sequence s
        where s.patient.id = :patientId
          and s.id < :currentSequenceId
        order by s.id desc
    """)
    List<Sequence> findPreviousByPatientAndCurrentId(
            @Param("patientId") Long patientId,
            @Param("currentSequenceId") Long currentSequenceId,
            Pageable pageable
    );

    @Query("""
        select s from Sequence s
        where s.patient.id = :patientId and s.id < :currentSequenceId
        order by s.id desc
    """)
    List<Sequence> findPreviousSequences(@Param("patientId") Long patientId, @Param("currentSequenceId") Long currentSequenceId, Pageable pageable);

    default Optional<Sequence> findLastSequence(Long patientId, Long currentSequenceId) {
        return findPreviousSequences(patientId, currentSequenceId, org.springframework.data.domain.PageRequest.of(0, 1))
                .stream().findFirst();
    }
}
