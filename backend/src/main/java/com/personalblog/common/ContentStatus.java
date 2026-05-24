package com.personalblog.common;

public final class ContentStatus {

    public static final String PUBLISHED = "published";
    public static final String DRAFT = "draft";

    private ContentStatus() {
    }

    public static String normalize(String value) {
        if (value == null || value.isBlank()) {
            return PUBLISHED;
        }
        String v = value.trim().toLowerCase();
        return DRAFT.equals(v) ? DRAFT : PUBLISHED;
    }
}
