package com.personalblog.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class AgentChatRequest {

    @NotBlank(message = "问题不能为空")
    private String question;

    @NotBlank(message = "sessionId 不能为空")
    private String sessionId;

    @Min(value = 1, message = "limit 至少为 1")
    @Max(value = 50, message = "limit 不能超过 50")
    private int limit = 5;
}
