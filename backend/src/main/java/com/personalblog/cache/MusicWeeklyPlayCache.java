package com.personalblog.cache;

import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * 按用户、按日记录曲目播放次数，用于汇总近 N 天（默认 7 天）播放排行。
 */
@Component
@RequiredArgsConstructor
public class MusicWeeklyPlayCache {

    private static final String DAILY_PREFIX = "music:play:daily:";

    private final StringRedisTemplate redisTemplate;

    @Value("${app.music.daily-key-ttl-days:8}")
    private int dailyKeyTtlDays;

    public void recordPlay(long userId, String trackId) {
        if (trackId == null || trackId.isBlank()) {
            return;
        }
        String key = dailyKey(userId, LocalDate.now());
        redisTemplate.opsForHash().increment(key, trackId.trim(), 1);
        redisTemplate.expire(key, dailyKeyTtlDays, TimeUnit.DAYS);
    }

    /** 汇总最近 {@code days} 天（含今天）各曲目的播放次数。 */
    public Map<String, Long> aggregateLastDays(long userId, int days) {
        if (days <= 0) {
            return Map.of();
        }
        Map<String, Long> totals = new HashMap<>();
        LocalDate today = LocalDate.now();
        for (int i = 0; i < days; i++) {
            String key = dailyKey(userId, today.minusDays(i));
            Map<Object, Object> entries = redisTemplate.opsForHash().entries(key);
            if (entries == null || entries.isEmpty()) {
                continue;
            }
            for (Map.Entry<Object, Object> entry : entries.entrySet()) {
                String trackId = String.valueOf(entry.getKey());
                long delta = parseCount(entry.getValue());
                if (delta > 0) {
                    totals.merge(trackId, delta, Long::sum);
                }
            }
        }
        return totals;
    }

    private static String dailyKey(long userId, LocalDate date) {
        return DAILY_PREFIX + userId + ":" + date;
    }

    private static long parseCount(Object value) {
        if (value == null) {
            return 0;
        }
        try {
            return Long.parseLong(value.toString());
        } catch (NumberFormatException ex) {
            return 0;
        }
    }
}
