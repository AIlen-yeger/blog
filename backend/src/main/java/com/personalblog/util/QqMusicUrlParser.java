package com.personalblog.util;

import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 从 QQ 音乐分享链接或文本中解析 songid。
 * 例：https://i.y.qq.com/v8/playsong.html?songid=238936765
 */
public final class QqMusicUrlParser {

    private static final Pattern[] PATTERNS = {
            Pattern.compile("[?&]songid=(\\d+)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("[?&]songmid=([A-Za-z0-9]+)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("/songDetail/(\\d+)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("songid[=:]\\s*(\\d+)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("^\\d{5,12}$"),
    };

    private QqMusicUrlParser() {
    }

    public static Optional<String> parseSongId(String input) {
        if (input == null) {
            return Optional.empty();
        }
        String text = input.trim();
        if (text.isEmpty()) {
            return Optional.empty();
        }
        for (Pattern pattern : PATTERNS) {
            Matcher matcher = pattern.matcher(text);
            if (matcher.find()) {
                String id = matcher.group(1).trim();
                if (!id.isEmpty()) {
                    return Optional.of(id);
                }
            }
        }
        return Optional.empty();
    }
}
