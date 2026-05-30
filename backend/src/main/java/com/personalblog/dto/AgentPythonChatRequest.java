package com.personalblog.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class AgentPythonChatRequest {

    private String question;

    @JsonProperty("session_id")
    private String sessionId;

    @JsonProperty("user_id")
    private long userId;

    private String account;

    @JsonProperty("user_name")
    private String userName;

    private int limit;

    @JsonProperty("access_token")
    private String accessToken;
}
