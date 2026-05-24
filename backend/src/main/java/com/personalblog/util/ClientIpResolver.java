package com.personalblog.util;

import jakarta.servlet.http.HttpServletRequest;

public final class ClientIpResolver {

    private ClientIpResolver() {
    }

    public static String resolveClientIp(HttpServletRequest request) {
        if (request == null) {
            return "unknown";
        }
        String xff = request.getHeader("X-Forwarded-For");
        if (xff != null && !xff.isBlank()) {
            return xff.split(",")[0].trim();
        }
        String realIp = request.getHeader("X-Real-IP");
        if (realIp != null && !realIp.isBlank()) {
            return realIp.trim();
        }
        String remote = request.getRemoteAddr();
        return remote != null && !remote.isBlank() ? remote.trim() : "unknown";
    }

    /** 匿名访客 Redis / DB 去重键 */
    public static String anonymousViewerKey(String ip) {
        return "ip:" + ip.replace(':', '_');
    }
}
