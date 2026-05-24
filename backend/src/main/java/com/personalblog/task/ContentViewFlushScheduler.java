package com.personalblog.task;

import com.personalblog.cache.ContentViewCache;
import com.personalblog.mapper.ContentViewMapper;
import com.personalblog.mapper.LifeMapper;
import com.personalblog.mapper.NoteMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.util.Set;

/**
 * 定时将 Redis 中的浏览增量与明细刷入 MySQL。
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class ContentViewFlushScheduler {

    private static final String TYPE_NOTE = "note";
    private static final String TYPE_LIFE = "life";

    private final ContentViewCache contentViewCache;
    private final ContentViewMapper contentViewMapper;
    private final NoteMapper noteMapper;
    private final LifeMapper lifeMapper;

    @Scheduled(fixedDelayString = "${app.view.flush-interval-ms:60000}")
    public void flushDirtyViews() {
        Set<String> dirty = contentViewCache.listDirtyMembers();
        if (dirty.isEmpty()) {
            return;
        }
        for (String member : dirty) {
            try {
                flushOne(member);
            } catch (Exception ex) {
                log.warn("[view-flush] 刷库失败 member={}, error={}", member, ex.getMessage());
            }
        }
    }

    @Transactional
    protected void flushOne(String member) {
        int sep = member.indexOf(':');
        if (sep <= 0 || sep >= member.length() - 1) {
            contentViewCache.removeDirtyMember(member);
            return;
        }
        String contentType = member.substring(0, sep);
        String contentId = member.substring(sep + 1);

        int delta = contentViewCache.getPendingCount(contentType, contentId);
        Set<String> viewers = contentViewCache.takeBatchViewers(contentType, contentId);

        if (delta > 0) {
            if (TYPE_NOTE.equals(contentType)) {
                noteMapper.incrementViewCountBy(contentId, delta);
            } else if (TYPE_LIFE.equals(contentType)) {
                lifeMapper.incrementViewCountBy(contentId, delta);
            }
            contentViewCache.takePendingCount(contentType, contentId);
        }

        for (String viewerKey : viewers) {
            contentViewMapper.insertIgnore(contentType, contentId, viewerKey);
        }

        if (delta <= 0 && viewers.isEmpty()) {
            contentViewCache.removeDirty(contentType, contentId);
            return;
        }

        contentViewCache.removeDirty(contentType, contentId);
        log.debug("[view-flush] {}:{} delta={} viewers={}", contentType, contentId, delta, viewers.size());
    }
}
