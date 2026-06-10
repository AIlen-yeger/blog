package com.personalblog.dto;

import lombok.Data;

@Data
public class AgentAttachmentDto {

    private String id;
    private String name;
    private String mime;
    private String url;
    /** image | document | text */
    private String kind;
    /** 内联文本（kind=text 且无 url 时） */
    private String text;
}
