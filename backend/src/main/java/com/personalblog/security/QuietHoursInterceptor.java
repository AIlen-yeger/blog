package com.personalblog.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.personalblog.common.ApiResponse;
import com.personalblog.common.ErrorCode;
import com.personalblog.config.QuietHoursProperties;
import com.personalblog.util.RequestClientIp;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.servlet.HandlerInterceptor;

import java.io.IOException;
import java.util.List;

/**
 * 夜间静默：开发者 JWT 全放行；POST /auth/login 交 Service 校验邮箱；其余 userId+IP 或白名单 IP 的 /auth。
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class QuietHoursInterceptor implements HandlerInterceptor {

    private final QuietHoursProperties quietHoursProperties;
    private final QuietHoursGuard quietHoursGuard;
    private final ObjectMapper objectMapper;
    private final AntPathMatcher pathMatcher = new AntPathMatcher();

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler)
            throws Exception {
        if (HttpMethod.OPTIONS.matches(request.getMethod())) {
            return true;
        }
        if (!quietHoursGuard.isActive()) {
            return true;
        }

        String path = request.getServletPath();
        if (matchesAny(path, quietHoursProperties.getBypassPathPatterns())) {
            return true;
        }

        if (isDeveloperPrincipal()) {
            return true;
        }

        if (HttpMethod.POST.matches(request.getMethod()) && "/auth/login".equals(path)) {
            return true;
        }

        String clientIp = normalizeIpLiteral(RequestClientIp.resolve(request));
        boolean ipAllowed = isIpAllowed(clientIp);

        if (quietHoursProperties.isAllowAuthFromWhitelistIp()
                && path.startsWith("/auth/")
                && ipAllowed) {
            return true;
        }

        long userId = resolveUserId();
        if (userId > 0 && isUserAllowed(userId) && ipAllowed) {
            return true;
        }

        log.info(
                "[quiet-hours] denied path={} ip={} userId={}",
                path,
                clientIp,
                userId > 0 ? userId : "guest");
        return writeQuietHours(response);
    }

    private boolean isDeveloperPrincipal() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || !(auth.getPrincipal() instanceof AuthUserPrincipal principal)) {
            return false;
        }
        return quietHoursGuard.isDeveloperEmail(principal.getEmail());
    }

    private boolean matchesAny(String path, List<String> patterns) {
        if (patterns == null || patterns.isEmpty()) {
            return false;
        }
        for (String pattern : patterns) {
            if (pattern != null && pathMatcher.match(pattern.trim(), path)) {
                return true;
            }
        }
        return false;
    }

    private boolean isIpAllowed(String clientIp) {
        List<String> ips = quietHoursProperties.getAllowIps();
        if (ips == null || ips.isEmpty()) {
            return false;
        }
        for (String ip : ips) {
            if (ip != null && normalizeIpLiteral(ip).equals(clientIp)) {
                return true;
            }
        }
        return false;
    }

    private static String normalizeIpLiteral(String ip) {
        String t = ip.trim();
        if ("0:0:0:0:0:0:0:1".equals(t)) {
            return "::1";
        }
        return t;
    }

    private boolean isUserAllowed(long userId) {
        List<Long> ids = quietHoursProperties.getAllowUserIds();
        if (ids == null || ids.isEmpty()) {
            return false;
        }
        return ids.contains(userId);
    }

    private long resolveUserId() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || !(auth.getPrincipal() instanceof AuthUserPrincipal principal)) {
            return 0L;
        }
        return principal.getUserId();
    }

    private boolean writeQuietHours(HttpServletResponse response) throws IOException {
        response.setStatus(HttpStatus.FORBIDDEN.value());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.setCharacterEncoding("UTF-8");
        objectMapper.writeValue(
                response.getWriter(),
                ApiResponse.fail(
                        ErrorCode.QUIET_HOURS.getCode(),
                        ErrorCode.QUIET_HOURS.getMessage()));
        return false;
    }
}
