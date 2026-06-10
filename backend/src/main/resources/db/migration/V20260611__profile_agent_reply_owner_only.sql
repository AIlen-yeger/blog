ALTER TABLE profile
    ADD COLUMN agent_reply_owner_only TINYINT(1) NOT NULL DEFAULT 0
        COMMENT '1=Agent 回复仅管理员可见' AFTER site_owner;
