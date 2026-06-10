package com.personalblog.dto;

import lombok.Data;

import java.util.List;

@Data
public class NoteWriteRequest {
    private String title;
    private String excerpt;
    private String tag;
    private String topicId;
    /** 专题名称：不存在时自动创建专题（与 topicId 二选一或同时传，优先有效 topicId） */
    private String topicTitle;
    private String content;
    private List<String> images;
    /** published | draft，默认 published */
    private String status;
    /** 桌宠会话 ID，用于拉近期聊天上下文生成 Kohaku 笔记回复（仅 create 时生效） */
    private String agentSessionId;
    /**
     * 是否在更新后重新生成 Agent 回复。默认 false；普通编辑不应触发。
     * 预留后续「基于 diff + 旧回复」的补充式回复。
     */
    private Boolean regenerateAgentReply;
}
