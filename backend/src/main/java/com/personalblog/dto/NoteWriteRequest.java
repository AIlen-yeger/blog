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
    /** 桌宠会话 ID，用于拉近期聊天上下文生成 Kohaku 笔记回复 */
    private String agentSessionId;
}
