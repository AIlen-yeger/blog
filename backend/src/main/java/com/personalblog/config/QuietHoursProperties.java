package com.personalblog.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.ArrayList;
import java.util.List;

/**
 * 夜间静默：云主机不关机，仅限制对外 API 访问。
 * 静默时段内：开发者邮箱可登录且 JWT 全放行；POST /auth/login 在 Service 校验邮箱；
 * 另支持白名单 userId+IP、白名单 IP 的其它 /auth（见 allow-auth-from-whitelist-ip）。
 */
@Data
@ConfigurationProperties(prefix = "app.quiet-hours")
public class QuietHoursProperties {

    /** 是否启用夜间限制 */
    private boolean enabled = false;

    /** 静默开始（含），如 23:00 */
    private String start = "23:00";

    /** 静默结束（不含），如 08:00；跨午夜时 start &gt; end */
    private String end = "08:00";

    /** 时区，如 Asia/Shanghai */
    private String zoneId = "Asia/Shanghai";

    /** 白名单用户 ID（须与 JWT userId 一致，且 IP 也在白名单） */
    private List<Long> allowUserIds = new ArrayList<>();

    /** 白名单客户端 IP（公网出口 IP；含 127.0.0.1 便于本机 Agent 回调经 Nginx 时按需配置） */
    private List<String> allowIps = new ArrayList<>();

    /**
     * 静默时段内，来自白名单 IP 是否允许访问 /auth/**（便于夜间登录拿 JWT）。
     */
    private boolean allowAuthFromWhitelistIp = true;

    /**
     * 始终放行的路径（Ant 风格），默认 Agent 内网 ops。
     */
    private List<String> bypassPathPatterns = new ArrayList<>(List.of("/agent/ops/**"));
}
