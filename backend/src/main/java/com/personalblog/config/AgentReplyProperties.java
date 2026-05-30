package com.personalblog.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

@Data
@ConfigurationProperties(prefix = "app.agent.reply")
public class AgentReplyProperties {
    /** 是否对笔记返回 Agent 回复 */
    private boolean noteEnabled = true;
    /** 是否对生活记录返回 Agent 回复 */
    private boolean lifeEnabled = true;
    /** 卡片预览建议最大字符数（供前端参考） */
    private int previewMaxChars = 120;
}
