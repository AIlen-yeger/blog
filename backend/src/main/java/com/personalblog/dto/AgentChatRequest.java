package com.personalblog.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class AgentChatRequest {

    @NotBlank(message = "问题不能为空")
    private String question;

    @NotBlank(message = "sessionId 不能为空")
    private String sessionId;

    @Min(value = 1, message = "limit 至少为 1")
    @Max(value = 50, message = "limit 不能超过 50")
    private int limit = 5;

    private List<AgentAttachmentDto> attachments = new ArrayList<>();

    /** auto | plan | fast */
    private String executionMode = "auto";

    /** 开启后 Agent 会先联网检索再回答 */
    private boolean enableWebSearch = false;
}
