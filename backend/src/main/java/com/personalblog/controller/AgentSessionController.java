package com.personalblog.controller;

import com.personalblog.common.ApiResponse;
import com.personalblog.common.BusinessException;
import com.personalblog.common.ErrorCode;
import com.personalblog.dto.AgentChatMessageDto;
import com.personalblog.dto.AgentSessionDto;
import com.personalblog.dto.AgentSessionTitleRequest;
import com.personalblog.entity.UserEntity;
import com.personalblog.mapper.UserMapper;
import com.personalblog.security.AuthUserPrincipal;
import com.personalblog.service.AiChatSessionService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/agent/sessions")
@RequiredArgsConstructor
public class AgentSessionController {

    private final AiChatSessionService sessionService;
    private final UserMapper userMapper;

    @GetMapping
    public ApiResponse<List<AgentSessionDto>> listSessions() {
        Long userId = currentUserId();
        return ApiResponse.ok(sessionService.listSessions(userId));
    }

    @PostMapping
    public ApiResponse<AgentSessionDto> createSession() {
        Long userId = currentUserId();
        return ApiResponse.ok(sessionService.createSession(userId));
    }

    @GetMapping("/{sessionId}/messages")
    public ApiResponse<List<AgentChatMessageDto>> listMessages(@PathVariable String sessionId) {
        Long userId = currentUserId();
        return ApiResponse.ok(sessionService.listMessages(userId, sessionId.trim()));
    }

    @PatchMapping("/{sessionId}")
    public ApiResponse<AgentSessionDto> updateTitle(
            @PathVariable String sessionId,
            @Valid @RequestBody AgentSessionTitleRequest request) {
        Long userId = currentUserId();
        return ApiResponse.ok(sessionService.updateTitle(userId, sessionId.trim(), request.getTitle()));
    }

    @DeleteMapping("/{sessionId}")
    public ApiResponse<Void> deleteSession(@PathVariable String sessionId) {
        Long userId = currentUserId();
        sessionService.deleteSession(userId, sessionId.trim());
        return ApiResponse.ok(null);
    }

    private Long currentUserId() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !(authentication.getPrincipal() instanceof AuthUserPrincipal principal)) {
            throw new BusinessException(ErrorCode.UNAUTHORIZED);
        }
        UserEntity user = userMapper.selectByEmail(principal.getEmail());
        if (user == null || user.getId() == null) {
            throw new BusinessException(ErrorCode.UNAUTHORIZED, "用户不存在");
        }
        return user.getId();
    }
}
