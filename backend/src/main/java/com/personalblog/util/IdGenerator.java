package com.personalblog.util;

import java.util.UUID;

public final class IdGenerator {

    private IdGenerator() {
    }

    public static String noteId() {
        return "n_" + System.currentTimeMillis() + "_" + UUID.randomUUID().toString().substring(0, 6);
    }

    public static String lifeId() {
        return "l_" + System.currentTimeMillis() + "_" + UUID.randomUUID().toString().substring(0, 6);
    }

    public static String topicId() {
        return "t_" + System.currentTimeMillis() + "_" + UUID.randomUUID().toString().substring(0, 6);
    }

    public static String musicTrackId() {
        return "m_" + System.currentTimeMillis() + "_" + UUID.randomUUID().toString().substring(0, 6);
    }

    public static String agentCommentJobId() {
        return "j_" + System.currentTimeMillis() + "_" + UUID.randomUUID().toString().substring(0, 8);
    }
}
