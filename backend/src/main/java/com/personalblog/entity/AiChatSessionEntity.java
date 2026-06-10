package com.personalblog.entity;

import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
public class AiChatSessionEntity {

    private String sessionId;
    private Long userId;
    /** 0=登录用户 1=访客 */
    private Integer guestFlag = 0;
    private String title = "新对话";
    private Integer msgCount = 0;
    private Long lastMsgId;
    private LocalDateTime lastActive;
    private LocalDateTime createTime;
}
