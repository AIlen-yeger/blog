package com.personalblog.util;

import jakarta.servlet.http.HttpServletRequest;

/** 解析客户端真实 IP（兼容 Nginx X-Forwarded-For / X-Real-IP）。 */
public final class RequestClientIp {

    private RequestClientIp() {
    }

    public static String resolve(HttpServletRequest request) {
        String xff = request.getHeader("X-Forwarded-For");
        if (xff != null && !xff.isBlank()) {
            for (String part : xff.split(",")) {
                String ip = part.trim();
                if (!ip.isEmpty() && !"unknown".equalsIgnoreCase(ip)) {
                    return normalize(ip);
                }
            }
        }
        String realIp = request.getHeader("X-Real-IP");
        if (realIp != null && !realIp.isBlank()) {
            return normalize(realIp.trim());
        }
        return normalize(request.getRemoteAddr());
    }

    private static String normalize(String ip) {
        if ("0:0:0:0:0:0:0:1".equals(ip)) {
            return "::1";
        }
        return ip;
    }
}
