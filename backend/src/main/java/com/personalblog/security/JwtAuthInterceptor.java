package com.personalblog.security;

import com.personalblog.common.ErrorCode;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.ILoggerFactory;
import org.springframework.http.HttpMethod;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

/**
 * JWT 鉴权拦截器：每次请求进入 Controller 前先解析并校验 Authorization 中的 JWT。
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class JwtAuthInterceptor implements HandlerInterceptor {

    private final JwtAuthenticationSupport jwtAuth;

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler)
            throws Exception {
        if (HttpMethod.OPTIONS.matches(request.getMethod())) {
            return true;
        }

        StringBuffer requestURL = request.getRequestURL();
        log.info("当前请求是：{}", requestURL.toString());

        String servletPath = request.getServletPath();
        if (isPublicPath(servletPath, request.getMethod())) {
            jwtAuth.resolvePrincipal(request).ifPresentOrElse(jwtAuth::setAuthentication, jwtAuth::clearAuthentication);
            return true;
        }

        if (jwtAuth.hasInvalidBearerToken(request)) {
            return jwtAuth.writeUnauthorized(response, ErrorCode.UNAUTHORIZED);
        }

        return jwtAuth.resolvePrincipal(request)
                .map(principal -> {
                    jwtAuth.setAuthentication(principal);
                    return true;
                })
                .orElseGet(() -> {
                    try {
                        return jwtAuth.writeUnauthorized(response, ErrorCode.UNAUTHORIZED);
                    } catch (Exception ex) {
                        return false;
                    }
                });
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response,
                                Object handler, Exception ex) {
        jwtAuth.clearAuthentication();
    }

    private boolean isPublicPath(String servletPath, String method) {
        if (servletPath.startsWith("/auth/")) {
            return true;
        }
        if (HttpMethod.POST.matches(method) && isViewRecordPath(servletPath)) {
            return true;
        }
        if (servletPath.startsWith("/uploads/") && HttpMethod.GET.matches(method)) {
            return true;
        }
        // 公开只读：游客可浏览已发布内容与管理员资料
        return isPublicReadPath(servletPath, method);
    }

    /** GET 只读接口：可选 JWT，无 token 时按游客处理 */
    private boolean isPublicReadPath(String servletPath, String method) {
        if (!HttpMethod.GET.matches(method)) {
            return false;
        }
        if ("/profile".equals(servletPath)
                || "/profile/public".equals(servletPath)
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

    /** 记录浏览：可选 JWT，未登录按匿名访客去重 */
    private boolean isViewRecordPath(String servletPath) {
        return servletPath.matches("/notes/[^/]+/views") || servletPath.matches("/life/[^/]+/views");
    }
}
