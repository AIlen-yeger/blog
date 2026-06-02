package com.personalblog.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

@Data
@ConfigurationProperties(prefix = "app.agent")
public class AgentProperties {

    /** Python Agent 内网地址，勿暴露公网 */
    private String baseUrl = "http://127.0.0.1:8000";

    private String chatPath = "/ai/chat";

    /** 笔记发布后 Kohaku 评论（内网，非 SSE） */
    private String noteCommentPath = "/ai/internal/note-comment";

    private int connectTimeoutMs = 5_000;

    /** 流式对话读超时（毫秒） */
    private int readTimeoutMs = 120_000;

    /** 笔记评论生成读超时（毫秒） */
    private int noteCommentReadTimeoutMs = 90_000;
}
