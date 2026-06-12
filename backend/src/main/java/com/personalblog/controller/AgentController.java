package com.personalblog.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.personalblog.common.BusinessException;
import com.personalblog.common.ErrorCode;
import com.personalblog.dto.AgentChatRequest;
import com.personalblog.dto.AgentPythonChatRequest;
import com.personalblog.entity.UserEntity;
import com.personalblog.mapper.UserMapper;
import com.personalblog.security.AuthUserPrincipal;
import com.personalblog.dto.ProfileDto;
import com.personalblog.service.AgentProxyService;
import com.personalblog.service.ProfileService;
import com.personalblog.util.AgentSseWriter;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import java.io.IOException;
import java.io.UncheckedIOException;

@RestController
@RequestMapping("/agent")
@RequiredArgsConstructor
@Slf4j
public class AgentController {

    private final AgentProxyService agentProxyService;
    private final ProfileService profileService;
    private final UserMapper userMapper;
    private final ObjectMapper objectMapper;

    @PostMapping("/chat")
    public ResponseEntity<StreamingResponseBody> chat(
            @Valid @RequestBody AgentChatRequest request,
            HttpServletRequest httpRequest) {
        try {
            AuthUserPrincipal principal = currentPrincipal();
            UserEntity user = userMapper.selectByEmail(principal.getEmail());
            if (user == null || user.getId() == null) {
                throw new BusinessException(ErrorCode.UNAUTHORIZED, "用户不存在");
            }

            String role = user.getRole() != null ? user.getRole().name() : "user";
            AgentPythonChatRequest upstream = new AgentPythonChatRequest(
                    request.getQuestion().trim(),
                    request.getSessionId().trim(),
                    user.getId(),
                    user.getEmail(),
                    displayName(user),
                    role,
                    request.getLimit(),
                    resolveBearerToken(httpRequest),
                    request.getAttachments() != null ? request.getAttachments() : java.util.List.of(),
                    normalizeExecutionMode(request.getExecutionMode()),
                    request.isEnableWebSearch()
            );

            StreamingResponseBody body = outputStream -> {
                try {
                    agentProxyService.streamChat(upstream, outputStream);
                } catch (BusinessException ex) {
                    AgentSseWriter.writeError(objectMapper, outputStream, ex);
                } catch (IOException ex) {
                    throw new UncheckedIOException(ex);
                } catch (Exception ex) {
                    log.warn("[agent/chat] stream failed", ex);
                    AgentSseWriter.writeError(
                            objectMapper,
                            outputStream,
                            new BusinessException(ErrorCode.INTERNAL_ERROR, "助手暂时不可用，请稍后重试"));
                }
            };

            return sseOk(body);
        } catch (BusinessException ex) {
            return sseError(ex);
        }
    }

    private ResponseEntity<StreamingResponseBody> sseOk(StreamingResponseBody body) {
        return ResponseEntity.ok()
                .contentType(MediaType.TEXT_EVENT_STREAM)
                .header("Cache-Control", "no-cache, no-transform")
                .header("Connection", "keep-alive")
                .header("X-Accel-Buffering", "no")
                .body(body);
    }

    private ResponseEntity<StreamingResponseBody> sseError(BusinessException ex) {
        StreamingResponseBody body = outputStream -> {
            try {
                AgentSseWriter.writeError(objectMapper, outputStream, ex);
            } catch (IOException ioEx) {
                throw new UncheckedIOException(ioEx);
            }
        };
        return sseOk(body);
    }

    private AuthUserPrincipal currentPrincipal() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !(authentication.getPrincipal() instanceof AuthUserPrincipal principal)) {
            throw new BusinessException(ErrorCode.UNAUTHORIZED);
        }
        return principal;
    }

    private String resolveBearerToken(HttpServletRequest request) {
        String auth = request.getHeader("Authorization");
        if (auth != null && auth.regionMatches(true, 0, "Bearer ", 0, 7)) {
            return auth.substring(7).trim();
        }
        return "";
    }

    private String displayName(UserEntity user) {
        if (user == null) {
            return "guest";
        }
        try {
            ProfileDto profile = profileService.getProfileByUserId(user.getId());
            if (profile != null && profile.getName() != null && !profile.getName().isBlank()) {
                return profile.getName().trim();
            }
        } catch (Exception ex) {
            log.debug("[agent/chat] profile name unavailable userId={}", user.getId());
        }
        return displayNameFromEmail(user.getEmail());
    }

    private static String normalizeExecutionMode(String mode) {
        if (mode == null || mode.isBlank()) {
            return "auto";
        }
        String key = mode.trim().toLowerCase();
        return switch (key) {
            case "plan", "fast" -> key;
            default -> "auto";
        };
    }

    private String displayNameFromEmail(String email) {
        if (email == null || email.isBlank()) {
            return "guest";
        }
        int at = email.indexOf('@');
        if (at <= 0) {
            return email;
        }
        return email.substring(0, at);
    }
}
