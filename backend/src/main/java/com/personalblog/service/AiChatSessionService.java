package com.personalblog.service;

import com.personalblog.dto.AgentChatMessageDto;
import com.personalblog.dto.AgentSessionDto;

import java.util.List;

public interface AiChatSessionService {

    List<AgentSessionDto> listSessions(Long userId);

    AgentSessionDto createSession(Long userId);

    List<AgentChatMessageDto> listMessages(Long userId, String sessionId);

    AgentSessionDto updateTitle(Long userId, String sessionId, String title);

    void deleteSession(Long userId, String sessionId);
}
