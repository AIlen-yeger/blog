package com.personalblog.entity;

import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
public class ContentAgentCommentJobEntity {

    private Long id;
    private String contentType;
    private String contentId;
    private String jobId;
    private String idempotencyKey;
    private String contentHash;
    private String sessionId;
    private long userId;
    private String status;
    private String agentReply;
    private String errorMessage;
    private String traceId;
    private LocalDateTime requestedAt;
    private LocalDateTime startedAt;
    private LocalDateTime completedAt;
}
