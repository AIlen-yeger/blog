ALTER TABLE notes
    ADD COLUMN owner_only TINYINT(1) NOT NULL DEFAULT 0
        COMMENT '1=仅管理员可见' AFTER status;

ALTER TABLE life_records
    ADD COLUMN owner_only TINYINT(1) NOT NULL DEFAULT 0
        COMMENT '1=仅管理员可见' AFTER status;
