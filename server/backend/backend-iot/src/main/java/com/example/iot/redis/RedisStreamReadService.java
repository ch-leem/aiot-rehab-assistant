package com.example.iot.redis;

import org.springframework.data.domain.Range;
import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.connection.Limit;
import org.springframework.data.redis.connection.stream.MapRecord;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class RedisStreamReadService {

    private final StringRedisTemplate redis;

    public String readLatestPayload(String streamKey) {
        // 최신부터 1개: XREVRANGE streamKey + - COUNT 1
        List<MapRecord<String, Object, Object>> records =
                redis.opsForStream().reverseRange(streamKey, Range.unbounded(), Limit.limit().count(1));

        if (records == null || records.isEmpty()) return null;

        Map<Object, Object> value = records.get(0).getValue();
        Object payload = value.get("payload"); // XADD ... payload '{json}'
        return payload == null ? null : payload.toString();
    }
}