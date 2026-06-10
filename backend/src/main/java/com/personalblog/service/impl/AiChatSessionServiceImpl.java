package com.personalblog.service.impl;

import com.personalblog.common.BusinessException;
import com.personalblog.common.ErrorCode;
import com.personalblog.dto.AgentChatMessageDto;
import com.personalblog.dto.AgentSessionDto;
import com.personalblog.entity.AiChatMessageEntity;
import com.personalblog.entity.AiChatSessionEntity;
import com.personalblog.mapper.AiChatMessageMapper;
import com.personalblog.mapper.AiChatSessionMapper;
import com.personalblog.service.AiChatSessionService;
import com.personalblog.util.IdGenerator;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.ZoneId;
import java.util.ArrayList;
import java.util.List;

@Service
@RequiredArgsConstructor
public class AiChatSessionServiceImpl implements AiChatSessionService {

    private static final String WEB_CHANNEL = "web";
    private static final int GUEST_FLAG_USER = 0;
    private static final ZoneId ZONE = ZoneId.of("Asia/Shanghai");

    private final AiChatSessionMapper sessionMapper;
    private final AiChatMessageMapper messageMapper;

    @Override
    public List<AgentSessionDto> listSessions(Long userId) {
        List<AiChatSessionEntity> rows = sessionMapper.listByUserId(userId);
        List<AgentSessionDto> out = new ArrayList<>(rows.size());
        for (AiChatSessionEntity row : rows) {
            out.add(toSessionDto(row));
        }
        return out;
    }

    @Override
    public AgentSessionDto createSession(Long userId) {
        AiChatSessionEntity entity = new AiChatSessionEntity();
        entity.setSessionId(IdGenerator.chatSessionId());
        entity.setUserId(userId);
        entity.setTitle("新对话");
        entity.setGuestFlag(GUEST_FLAG_USER);
        entity.setMsgCount(0);
        sessionMapper.insert(entity);
        AiChatSessionEntity saved = sessionMapper.selectBySessionIdAndUserId(entity.getSessionId(), userId);
        return toSessionDto(saved != null ? saved : entity);
    }

    @Override
    public List<AgentChatMessageDto> listMessages(Long userId, String sessionId) {
        requireOwnedSession(userId, sessionId);
        List<AiChatMessageEntity> rows = messageMapper.listBySession(sessionId, userId, WEB_CHANNEL);
        List<AgentChatMessageDto> out = new ArrayList<>(rows.size());
        for (AiChatMessageEntity row : rows) {
            out.add(toMessageDto(row));
        }
        return out;
    }

    @Override
    public AgentSessionDto updateTitle(Long userId, String sessionId, String title) {
        requireOwnedSession(userId, sessionId);
        String trimmed = title.trim();
        if (trimmed.isEmpty()) {
            throw new BusinessException(ErrorCode.TITLE_REQUIRED);
        }
        String normalized = trimmed.length() > 255 ? trimmed.substring(0, 255) : trimmed;
        sessionMapper.updateTitle(sessionId, userId, normalized);
        AiChatSessionEntity saved = sessionMapper.selectBySessionIdAndUserId(sessionId, userId);
        return toSessionDto(saved);
    }

    @Override
    @Transactional
    public void deleteSession(Long userId, String sessionId) {
        requireOwnedSession(userId, sessionId);
        messageMapper.deleteBySessionIdAndUserId(sessionId, userId, WEB_CHANNEL);
        sessionMapper.deleteBySessionIdAndUserId(sessionId, userId);
    }

    private AiChatSessionEntity requireOwnedSession(Long userId, String sessionId) {
        AiChatSessionEntity row = sessionMapper.selectBySessionIdAndUserId(sessionId, userId);
        if (row == null) {
            throw new BusinessException(ErrorCode.AGENT_SESSION_NOT_FOUND);
        }
        return row;
    }

    private AgentSessionDto toSessionDto(AiChatSessionEntity row) {
        if (row == null) {
            return null;
        }
        return new AgentSessionDto(
                row.getSessionId(),
                row.getTitle(),
                toEpochMillis(row.getCreateTime()),
                toEpochMillis(row.getLastActive()));
    }

    private AgentChatMessageDto toMessageDto(AiChatMessageEntity row) {
        return new AgentChatMessageDto(
                row.getId(),
                row.getRole(),
                row.getContent(),
                toEpochMillis(row.getCreateTime()));
    }

    private long toEpochMillis(java.time.LocalDateTime time) {
        if (time == null) {
            return System.currentTimeMillis();
        }
        return time.atZone(ZONE).toInstant().toEpochMilli();
    }
}
