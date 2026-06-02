package com.personalblog.util;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

public final class AgentContentHash {

    private AgentContentHash() {
    }

    /** 笔记/生活记录正文指纹，用于幂等键。 */
    public static String sha256NoteContent(String title, String content) {
        String safeTitle = title == null ? "" : title.trim();
        String safeContent = content == null ? "" : content.trim();
        return sha256Hex(safeTitle + "\n" + safeContent);
    }

    public static String idempotencyKey(String contentType, String contentId, String contentHash) {
        return contentType + ":" + contentId + ":" + contentHash;
    }

    private static String sha256Hex(String input) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(input.getBytes(StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder(hash.length * 2);
            for (byte b : hash) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 unavailable", ex);
        }
    }
}
