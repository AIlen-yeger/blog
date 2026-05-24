package com.personalblog.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

@Data
@ConfigurationProperties(prefix = "app.view")
public class ContentViewProperties {

    /** 浏览增量刷入 MySQL 的间隔（毫秒） */
    private long flushIntervalMs = 60_000L;
}
