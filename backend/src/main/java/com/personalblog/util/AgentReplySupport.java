package com.personalblog.util;

import com.personalblog.config.AgentReplyProperties;

/** Agent 回复在 API 层的呈现规则。 */
public final class AgentReplySupport {

    private AgentReplySupport() {
    }

    public static String presentForNote(
            AgentReplyProperties props,
            String raw,
            boolean viewerIsAdmin,
            boolean ownerOnlyVisible) {
        if (props == null || !props.isNoteEnabled()) {
            return null;
        }
        if (ownerOnlyVisible && !viewerIsAdmin) {
            return null;
        }
        return blankToNull(raw);
    }

    public static String presentForLife(
            AgentReplyProperties props,
            String raw,
            boolean viewerIsAdmin,
            boolean ownerOnlyVisible) {
        if (props == null || !props.isLifeEnabled()) {
            return null;
        }
        if (ownerOnlyVisible && !viewerIsAdmin) {
            return null;
        }
        return blankToNull(raw);
    }

    public static String presentNoteStatus(
            String status,
            boolean viewerIsAdmin,
            boolean ownerOnlyVisible) {
        if (ownerOnlyVisible && !viewerIsAdmin) {
            return "none";
        }
        if (status == null || status.isBlank()) {
            return "none";
        }
        return status.trim();
    }

    private static String blankToNull(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim();
    }
}
