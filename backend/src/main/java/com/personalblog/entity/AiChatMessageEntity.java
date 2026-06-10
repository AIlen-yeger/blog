package com.personalblog.entity;

import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
public class AiChatMessageEntity {

    private Long id;
    private String sessionId;
    private Long userId;
    private String channel = "web";
    private String role;
    private String content;
    private LocalDateTime createTime;
}
