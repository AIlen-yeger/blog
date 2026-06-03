-- 已有库执行一次；若 channel 已存在可跳过
ALTER TABLE ai_chat_message
    ADD COLUMN channel VARCHAR(16) NOT NULL DEFAULT 'web' COMMENT 'web | qq | internal' AFTER user_id;

ALTER TABLE ai_chat_message
    ADD INDEX idx_chat_session_channel (session_id, user_id, channel, id);
