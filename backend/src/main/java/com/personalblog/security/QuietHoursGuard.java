package com.personalblog.security;

import com.personalblog.common.BusinessException;
import com.personalblog.common.ErrorCode;
import com.personalblog.config.QuietHoursProperties;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.time.LocalTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;

/**
 * 夜间静默时段判断；登录仅允许 {@code developer.email}。
 */
@Component
public class QuietHoursGuard {

    private final QuietHoursProperties quietHoursProperties;

    @Value("${developer.email:}")
    private String developerEmail;

    public QuietHoursGuard(QuietHoursProperties quietHoursProperties) {
        this.quietHoursProperties = quietHoursProperties;
    }

    public boolean isEnabled() {
        return quietHoursProperties.isEnabled();
    }

    public boolean isWithinQuietHours() {
        if (!quietHoursProperties.isEnabled()) {
            return false;
        }
        ZoneId zone;
        try {
            zone = ZoneId.of(quietHoursProperties.getZoneId());
        } catch (Exception ex) {
            zone = ZoneId.systemDefault();
        }
        LocalTime now = ZonedDateTime.now(zone).toLocalTime();
        LocalTime start = parseTime(quietHoursProperties.getStart(), LocalTime.of(23, 0));
        LocalTime end = parseTime(quietHoursProperties.getEnd(), LocalTime.of(8, 0));

        if (start.equals(end)) {
            return false;
        }
        if (start.isBefore(end)) {
            return !now.isBefore(start) && now.isBefore(end);
        }
        return !now.isBefore(start) || now.isBefore(end);
    }

    public boolean isActive() {
        return isEnabled() && isWithinQuietHours();
    }

    public boolean isDeveloperEmail(String email) {
        if (email == null || email.isBlank() || developerEmail == null || developerEmail.isBlank()) {
            return false;
        }
        return developerEmail.trim().equalsIgnoreCase(email.trim());
    }

    /** 静默时段内，非开发者邮箱禁止登录 */
    public void requireDeveloperLogin(String normalizedEmail) {
        if (isActive() && !isDeveloperEmail(normalizedEmail)) {
            throw new BusinessException(ErrorCode.QUIET_HOURS);
        }
    }

    private static LocalTime parseTime(String raw, LocalTime fallback) {
        if (raw == null || raw.isBlank()) {
            return fallback;
        }
        try {
            return LocalTime.parse(raw.trim());
        } catch (Exception ex) {
            return fallback;
        }
    }
}
