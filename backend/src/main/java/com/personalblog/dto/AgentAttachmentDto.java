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
}
