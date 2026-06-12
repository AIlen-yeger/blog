package com.personalblog.dto;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class AgentPythonChatRequest {

    private String question;
    private String sessionId;
    private long userId;
    private String account;
    private String userName;
    private String userRole;
    private int limit;
    private String accessToken;
    private List<AgentAttachmentDto> attachments = new ArrayList<>();
    private String executionMode = "auto";
    private boolean enableWebSearch = false;
}
