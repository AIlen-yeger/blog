package com.personalblog.service.impl;

import com.personalblog.cache.ContentViewCache;
import com.personalblog.common.BusinessException;
import com.personalblog.common.ContentStatus;
import com.personalblog.common.ErrorCode;
import com.personalblog.entity.LifeEntity;
import com.personalblog.entity.NoteEntity;
import com.personalblog.security.AdminGuard;
import com.personalblog.dto.ViewRecordResultDto;
import com.personalblog.mapper.LifeMapper;
import com.personalblog.mapper.NoteMapper;
import com.personalblog.security.AuthUserPrincipal;
import com.personalblog.service.ContentViewService;
import com.personalblog.util.ClientIpResolver;
import com.personalblog.util.ContentVisibilitySupport;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class ContentViewServiceImpl implements ContentViewService {

    private static final String TYPE_NOTE = "note";
    private static final String TYPE_LIFE = "life";

    private final ContentViewCache contentViewCache;
    private final NoteMapper noteMapper;
    private final LifeMapper lifeMapper;
    private final AdminGuard adminGuard;

    @Override
    public ViewRecordResultDto recordNoteView(String noteId, HttpServletRequest request) {
        NoteEntity entity = noteMapper.selectById(noteId);
        assertViewable(entity);
        return recordView(TYPE_NOTE, noteId, request);
    }

    @Override
    public ViewRecordResultDto recordLifeView(String lifeId, HttpServletRequest request) {
        LifeEntity entity = lifeMapper.selectById(lifeId);
        assertViewable(entity);
        return recordView(TYPE_LIFE, lifeId, request);
    }

    private void assertViewable(NoteEntity entity) {
        ContentVisibilitySupport.assertNoteReadable(entity, adminGuard);
    }

    private void assertViewable(LifeEntity entity) {
        ContentVisibilitySupport.assertLifeReadable(entity, adminGuard);
    }

    private ViewRecordResultDto recordView(String contentType, String contentId, HttpServletRequest request) {
        String viewerKey = resolveViewerKey(request);
        int dbCount = TYPE_NOTE.equals(contentType)
                ? noteMapper.selectViewCount(contentId)
                : lifeMapper.selectViewCount(contentId);

        boolean recorded = contentViewCache.tryRecord(contentType, contentId, viewerKey);
        int viewCount = contentViewCache.getDisplayCount(contentType, contentId, dbCount);
        return new ViewRecordResultDto(viewCount, recorded);
    }

    private String resolveViewerKey(HttpServletRequest request) {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getPrincipal() instanceof AuthUserPrincipal principal) {
            return principal.getEmail().trim().toLowerCase();
        }
        return ClientIpResolver.anonymousViewerKey(ClientIpResolver.resolveClientIp(request));
    }
}
