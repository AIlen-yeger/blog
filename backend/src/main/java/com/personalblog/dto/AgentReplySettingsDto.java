package com.personalblog.dto;

import lombok.Builder;
import lombok.Data;

/** 前端展示 Kohaku 自动回复的全局开关（与 app.agent.reply 配置一致）。 */
@Data
@Builder
public class AgentReplySettingsDto {
    private boolean noteEnabled;
    private boolean lifeEnabled;
    /** 卡片预览最大字符数 */
    private int previewMaxChars;
    /** 为 true 时仅管理员可见 Agent 回复（访客 API 不返回正文） */
    private boolean ownerOnlyVisible;
}
