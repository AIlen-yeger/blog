package com.personalblog.controller;

import com.personalblog.common.BusinessException;
import com.personalblog.common.ErrorCode;
import com.personalblog.dto.AgentChatRequest;
import com.personalblog.dto.AgentPythonChatRequest;
import com.personalblog.entity.UserEntity;
import com.personalblog.mapper.UserMapper;
import com.personalblog.security.AuthUserPrincipal;
import com.personalblog.service.AgentProxyService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
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
public class AgentController {

    private final AgentProxyService agentProxyService;
    private final UserMapper userMapper;

    @PostMapping(value = "/chat", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public ResponseEntity<StreamingResponseBody> chat(@Valid @RequestBody AgentChatRequest request) {
        AuthUserPrincipal principal = currentPrincipal();
        UserEntity user = userMapper.selectByEmail(principal.getEmail());
        if (user == null || user.getId() == null) {
            throw new BusinessException(ErrorCode.UNAUTHORIZED, "用户不存在");
        }

        AgentPythonChatRequest upstream = new AgentPythonChatRequest(
                request.getQuestion().trim(),
                request.getSessionId().trim(),
                user.getId(),
                user.getEmail(),
                displayName(user.getEmail()),
                request.getLimit()
        );

        StreamingResponseBody body = outputStream -> {
            try {
                agentProxyService.streamChat(upstream, outputStream);
            } catch (IOException ex) {
                throw new UncheckedIOException(ex);
            }
        };

        return ResponseEntity.ok()
                .contentType(MediaType.TEXT_EVENT_STREAM)
                .header("Cache-Control", "no-cache, no-transform")
                .header("Connection", "keep-alive")
                .header("X-Accel-Buffering", "no")
                .body(body);
    }

    private AuthUserPrincipal currentPrincipal() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !(authentication.getPrincipal() instanceof AuthUserPrincipal principal)) {
            throw new BusinessException(ErrorCode.UNAUTHORIZED);
        }
        return principal;
    }

    private String displayName(String email) {
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
