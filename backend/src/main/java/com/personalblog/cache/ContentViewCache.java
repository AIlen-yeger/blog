package com.personalblog.cache;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.util.Collections;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * 浏览记录 Redis 缓存：去重集合 + 待刷库增量 + 脏数据标记。
 * 展示浏览量 = DB view_count + pending 增量。
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class ContentViewCache {

    private static final String SEEN_PREFIX = "view:seen:";
    private static final String PENDING_PREFIX = "view:pending:";
    private static final String BATCH_PREFIX = "view:batch:";
    private static final String DIRTY_KEY = "view:dirty";

    private final StringRedisTemplate redisTemplate;

    /**
     * 尝试记录浏览；若 viewerKey 已存在则返回 false。
     */
    public boolean tryRecord(String contentType, String contentId, String viewerKey) {
        try {
            String seenKey = seenKey(contentType, contentId);
            Long added = redisTemplate.opsForSet().add(seenKey, viewerKey);
            if (added == null || added == 0) {
                return false;
            }
            redisTemplate.opsForValue().increment(pendingKey(contentType, contentId));
            redisTemplate.opsForSet().add(batchKey(contentType, contentId), viewerKey);
            redisTemplate.opsForSet().add(DIRTY_KEY, dirtyMember(contentType, contentId));
            return true;
        } catch (Exception ex) {
            log.warn("[view-cache] Redis 不可用，跳过浏览记录: {}", ex.getMessage());
            return false;
        }
    }

    public int getPendingCount(String contentType, String contentId) {
        try {
            String raw = redisTemplate.opsForValue().get(pendingKey(contentType, contentId));
            if (raw == null || raw.isBlank()) {
                return 0;
            }
            return Integer.parseInt(raw);
        } catch (NumberFormatException ex) {
            return 0;
        } catch (Exception ex) {
            log.warn("[view-cache] 读取 pending 失败: {}", ex.getMessage());
            return 0;
        }
    }

    /** 展示用总浏览量 = 库内已持久化 + Redis 待刷增量 */
    public int getDisplayCount(String contentType, String contentId, int dbCount) {
        return dbCount + getPendingCount(contentType, contentId);
    }

    public Set<String> listDirtyMembers() {
        Set<String> members = redisTemplate.opsForSet().members(DIRTY_KEY);
        if (members == null || members.isEmpty()) {
            return Collections.emptySet();
        }
        return members;
    }

    /** 取出并清零待刷增量 */
    public int takePendingCount(String contentType, String contentId) {
        String key = pendingKey(contentType, contentId);
        String raw = redisTemplate.opsForValue().get(key);
        if (raw != null) {
            redisTemplate.delete(key);
        }
        if (raw == null || raw.isBlank()) {
            return 0;
        }
        try {
            return Integer.parseInt(raw);
        } catch (NumberFormatException ex) {
            return 0;
        }
    }

    /** 取出本批待写入 content_views 的 viewerKey */
    public Set<String> takeBatchViewers(String contentType, String contentId) {
        String key = batchKey(contentType, contentId);
        Set<String> members = redisTemplate.opsForSet().members(key);
        redisTemplate.delete(key);
        if (members == null || members.isEmpty()) {
            return Collections.emptySet();
        }
        return members.stream().filter(v -> v != null && !v.isBlank()).collect(Collectors.toSet());
    }

    public void removeDirty(String contentType, String contentId) {
        redisTemplate.opsForSet().remove(DIRTY_KEY, dirtyMember(contentType, contentId));
    }

    public void removeDirtyMember(String member) {
        redisTemplate.opsForSet().remove(DIRTY_KEY, member);
    }

    private String seenKey(String contentType, String contentId) {
        return SEEN_PREFIX + contentType + ":" + contentId;
    }

    private String pendingKey(String contentType, String contentId) {
        return PENDING_PREFIX + contentType + ":" + contentId;
    }

    private String batchKey(String contentType, String contentId) {
        return BATCH_PREFIX + contentType + ":" + contentId;
    }

    private String dirtyMember(String contentType, String contentId) {
        return contentType + ":" + contentId;
    }
}
