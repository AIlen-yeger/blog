package com.personalblog.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class PublishNoteActionRequest {

    @NotBlank(message = "标题不能为空")
    private String title;

    @NotBlank(message = "正文不能为空")
    private String content;

    private String topicTitle = "随笔";

    private String sessionId;

    private String status = "published";
}
