package com.personalblog.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.personalblog.common.ApiResponse;
import com.personalblog.common.ErrorCode;
import com.personalblog.entity.UserRole;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.Optional;

/**
 * JWT 解析与校验（签名、过期、角色），供拦截器在每次请求进入 Controller 前调用。
 */
@Component
@RequiredArgsConstructor
public class JwtAuthenticationSupport {

    private final JwtService jwtService;
    private final ObjectMapper objectMapper;

    public Optional<String> extractBearerToken(HttpServletRequest request) {
        String header = request.getHeader(HttpHeaders.AUTHORIZATION);
        if (header == null || !header.startsWith("Bearer ")) {
            return Optional.empty();
        }
        String token = header.substring(7).trim();
        return token.isEmpty() ? Optional.empty() : Optional.of(token);
    }

    public Optional<AuthUserPrincipal> parsePrincipal(String token) {
        try {
            Claims claims = jwtService.parseClaims(token);
            String email = claims.getSubject();
            String roleStr = claims.get("role", String.class);
            if (email == null || email.isBlank() || roleStr == null) {
                return Optional.empty();
            }
            UserRole role = UserRole.valueOf(roleStr);
            long userId = 0L;
            Object uid = claims.get("userId");
            if (uid instanceof Number number) {
                userId = number.longValue();
            }
            return Optional.of(new AuthUserPrincipal(userId, email, role));
        } catch (JwtException | IllegalArgumentException ex) {
            return Optional.empty();
        }
    }

    public Optional<AuthUserPrincipal> resolvePrincipal(HttpServletRequest request) {
        return extractBearerToken(request).flatMap(this::parsePrincipal);
    }

    public void setAuthentication(AuthUserPrincipal principal) {
        UsernamePasswordAuthenticationToken auth =
                new UsernamePasswordAuthenticationToken(principal, null, principal.getAuthorities());
        SecurityContextHolder.getContext().setAuthentication(auth);
    }

    public void clearAuthentication() {
        SecurityContextHolder.clearContext();
    }

    /** 请求头带了 token 但解析失败（伪造/过期） */
    public boolean hasInvalidBearerToken(HttpServletRequest request) {
        Optional<String> token = extractBearerToken(request);
        return token.isPresent() && parsePrincipal(token.get()).isEmpty();
    }

    public boolean writeUnauthorized(HttpServletResponse response, ErrorCode errorCode) throws IOException {
        response.setStatus(HttpStatus.UNAUTHORIZED.value());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.setCharacterEncoding("UTF-8");
        objectMapper.writeValue(response.getWriter(), ApiResponse.fail(errorCode));
        return false;
    }
}
