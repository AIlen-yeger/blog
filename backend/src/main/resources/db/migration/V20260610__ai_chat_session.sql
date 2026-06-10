CREATE TABLE IF NOT EXISTS ai_chat_session (
    session_id   VARCHAR(128) NOT NULL PRIMARY KEY,
    user_id      BIGINT       NOT NULL,
    guest_flag   TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '0=登录用户 1=访客',
    title        VARCHAR(255) NOT NULL DEFAULT '新对话',
    msg_count    INT          NOT NULL DEFAULT 0,
    last_msg_id  BIGINT       NULL,
    last_active  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    create_time  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_chat_session_user (user_id, last_active DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Agent Web 对话会话';
