package com.personalblog.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

@Data
@ConfigurationProperties(prefix = "app.tencent.ses")
public class TencentSesProperties {

    /** 地域，如 ap-guangzhou */
    private String region = "ap-guangzhou";

    /** API 端点，国内站默认 ses.tencentcloudapi.com */
    private String endpoint = "ses.tencentcloudapi.com";

    /**
     * 可留空，优先读环境变量：
     * TENCENTCLOUD_SECRET_ID / TENCENTCLOUD_SECRET_KEY，或 SecretId / SecretKey。
     */
    private String secretId = "";

    private String secretKey = "";
}
