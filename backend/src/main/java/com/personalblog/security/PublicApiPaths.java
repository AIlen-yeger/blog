package com.personalblog.security;

import org.springframework.http.HttpMethod;

/** 游客可访问的公开 API 路径（JWT 可选、夜间静默对只读放行）。 */
public final class PublicApiPaths {

    private PublicApiPaths() {
    }

    public static boolean isPublicPath(String servletPath, String method) {
        if (servletPath.startsWith("/auth/")) {
            return true;
        }
        if (HttpMethod.POST.matches(method) && isViewRecordPath(servletPath)) {
            return true;
        }
        if (HttpMethod.POST.matches(method) && servletPath.startsWith("/agent/ops/")) {
            return true;
        }
        if (HttpMethod.POST.matches(method) && "/music/parse".equals(servletPath)) {
            return true;
        }
        if (HttpMethod.POST.matches(method) && servletPath.matches("/music/tracks/[^/]+/play")) {
            return true;
        }
        if (servletPath.startsWith("/uploads/") && HttpMethod.GET.matches(method)) {
            return true;
        }
        return isPublicReadPath(servletPath, method);
    }

    /** 夜间静默仍允许的游客访问：公开只读 GET + 上传静态资源 + 浏览量 POST */
    public static boolean isAnonymousReadable(String servletPath, String method) {
        if (servletPath.startsWith("/uploads/") && HttpMethod.GET.matches(method)) {
            return true;
        }
        if (isPublicReadPath(servletPath, method)) {
            return true;
        }
        return HttpMethod.POST.matches(method) && isViewRecordPath(servletPath);
    }

    public static boolean isPublicReadPath(String servletPath, String method) {
        if (!HttpMethod.GET.matches(method)) {
            return false;
        }
        if ("/profile/public".equals(servletPath)
                || servletPath.matches("/profile/users/\\d+")
                || "/check-ins/site-owner".equals(servletPath)
                || "/music/site-owner".equals(servletPath)
                || "/topics".equals(servletPath)
                || "/timeline".equals(servletPath)
                || "/search".equals(servletPath)
                || "/notes".equals(servletPath)
                || "/life".equals(servletPath)) {
            return true;
        }
        if (servletPath.startsWith("/meta/")) {
            return true;
        }
        if (servletPath.matches("/notes/[^/]+") && !servletPath.endsWith("/views")) {
            return true;
        }
        return servletPath.matches("/life/[^/]+") && !servletPath.endsWith("/views");
    }

    private static boolean isViewRecordPath(String servletPath) {
        return servletPath.matches("/notes/[^/]+/views") || servletPath.matches("/life/[^/]+/views");
    }
}
