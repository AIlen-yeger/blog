package com.personalblog.util;

public final class ExcerptUtil {

    private static final int MAX_LEN = 48;

    private ExcerptUtil() {
    }

    public static String fromContent(String excerpt, String content) {
        if (excerpt != null && !excerpt.isBlank()) {
            return excerpt.trim();
        }
        if (content == null || content.isBlank()) {
            return "";
        }
        String plain = content.replaceAll("[#*`>\\-\\[\\]]", "").replaceAll("\\s+", " ").trim();
        if (plain.length() <= MAX_LEN) {
            return plain;
        }
        return plain.substring(0, MAX_LEN);
    }
}
