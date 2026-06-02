package com.personalblog.security;

import com.personalblog.common.ErrorCode;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
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
        if (PublicApiPaths.isPublicPath(servletPath, request.getMethod())) {
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

}
