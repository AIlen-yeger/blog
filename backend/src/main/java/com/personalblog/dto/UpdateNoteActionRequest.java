package com.personalblog.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class UpdateNoteActionRequest {

    @NotBlank(message = "noteId 不能为空")
    private String noteId;

    @NotBlank(message = "标题不能为空")
    private String title;

    @NotBlank(message = "正文不能为空")
    private String content;

    private String topicTitle;

    private String status;
}
