-- Agent 评价任务表 + notes 状态字段（若已手工建表可跳过）
-- mysql -u root -p myblog < backend/src/main/resources/db/migration-content-agent-comment-job.sql

USE myblog;

CREATE TABLE IF NOT EXISTS content_agent_comment_job (
    id                BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    content_type      VARCHAR(16)  NOT NULL COMMENT 'note | life',
    content_id        VARCHAR(64)  NOT NULL,
    job_id            VARCHAR(64)  NOT NULL,
    idempotency_key   VARCHAR(128) NOT NULL,
    content_hash      CHAR(64)     NOT NULL,
    session_id        VARCHAR(128) NULL,
    user_id           BIGINT       NOT NULL DEFAULT 0,
    status            VARCHAR(16)  NOT NULL DEFAULT 'pending',
    agent_reply       MEDIUMTEXT   NULL,
    error_message     VARCHAR(512) NULL,
    trace_id          VARCHAR(64)  NULL,
    requested_at      DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    started_at        DATETIME(3)  NULL,
    completed_at      DATETIME(3)  NULL,
    UNIQUE KEY uk_agent_comment_idempotency (idempotency_key),
    KEY idx_agent_comment_content (content_type, content_id, status),
    KEY idx_agent_comment_job (job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Kohaku 内容评价生成任务';

ALTER TABLE notes
    ADD COLUMN agent_reply_status VARCHAR(16) NOT NULL DEFAULT 'none' AFTER status,
    ADD COLUMN agent_reply_job_id VARCHAR(64) NULL AFTER agent_reply;
