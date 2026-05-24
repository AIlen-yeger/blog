package com.personalblog.cache;

import com.personalblog.common.BusinessException;
import com.personalblog.common.ErrorCode;
import com.personalblog.util.JsonUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.concurrent.TimeUnit;

/**
 * 注册验证码 Redis 缓存：验证码 + 密码哈希、60s 重发冷却、每日发送次数上限。
 */
@Component
@RequiredArgsConstructor
public class RegisterCodeCache {

    private static final String PENDING_PREFIX = "register:pending:";
    private static final String COOLDOWN_PREFIX = "register:cooldown:";
    private static final String DAILY_PREFIX = "register:daily:";

    private final StringRedisTemplate redisTemplate;

    @Value("${app.register.code-ttl-seconds:300}")
    private int codeTtlSeconds;

    @Value("${app.register.resend-cooldown-seconds:60}")
    private int resendCooldownSeconds;

    @Value("${app.register.daily-send-limit:8}")
    private int dailySendLimit;

    public int getCodeTtlSeconds() {
        return codeTtlSeconds;
    }

    public boolean isInCooldown(String email) {
        return Boolean.TRUE.equals(redisTemplate.hasKey(cooldownKey(email)));
    }

    public void checkAndRecordDailySend(String email) {
        String key = dailyKey(email);
        Long count = redisTemplate.opsForValue().increment(key);
        if (count != null && count == 1) {
            redisTemplate.expire(key, secondsUntilEndOfDay(), TimeUnit.SECONDS);
        }
        if (count != null && count > dailySendLimit) {
            throw new BusinessException(ErrorCode.CODE_DAILY_LIMIT);
        }
    }

    public void savePending(String email, String code, String passwordHash) {
        RegisterPendingData data = new RegisterPendingData(code, passwordHash);
        redisTemplate.opsForValue().set(
                pendingKey(email),
                JsonUtil.toJson(data),
                Duration.ofSeconds(codeTtlSeconds));
        redisTemplate.opsForValue().set(
                cooldownKey(email),
                "1",
                Duration.ofSeconds(resendCooldownSeconds));
    }

    public RegisterPendingData getPending(String email) {
        String json = redisTemplate.opsForValue().get(pendingKey(email));
        if (json == null || json.isBlank()) {
            return null;
        }
        return JsonUtil.fromObject(json, RegisterPendingData.class);
    }

    public void clearPending(String email) {
        redisTemplate.delete(pendingKey(email));
        redisTemplate.delete(cooldownKey(email));
    }

    private String pendingKey(String email) {
        return PENDING_PREFIX + email;
    }

    private String cooldownKey(String email) {
        return COOLDOWN_PREFIX + email;
    }

    private String dailyKey(String email) {
        return DAILY_PREFIX + email + ":" + LocalDate.now();
    }

    private long secondsUntilEndOfDay() {
        LocalDateTime end = LocalDate.now().plusDays(1).atTime(LocalTime.MIN);
        return Duration.between(LocalDateTime.now(), end).getSeconds();
    }
}
