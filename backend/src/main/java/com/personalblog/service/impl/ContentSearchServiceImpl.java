package com.personalblog.service.impl;

import com.personalblog.common.ContentStatus;
import com.personalblog.config.AgentReplyProperties;
import com.personalblog.dto.LifeDto;
import com.personalblog.dto.NoteDto;
import com.personalblog.dto.SearchResultDto;
import com.personalblog.entity.LifeEntity;
import com.personalblog.entity.NoteEntity;
import com.personalblog.cache.ContentViewCache;
import com.personalblog.mapper.LifeMapper;
import com.personalblog.mapper.NoteMapper;
import com.personalblog.security.AdminGuard;
import com.personalblog.service.ContentSearchService;
import com.personalblog.util.AgentReplySupport;
import com.personalblog.util.JsonUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class ContentSearchServiceImpl implements ContentSearchService {

    private final NoteMapper noteMapper;
    private final LifeMapper lifeMapper;
    private final ContentViewCache contentViewCache;
    private final AdminGuard adminGuard;
    private final AgentReplyProperties agentReplyProperties;

    @Override
    public SearchResultDto search(String keyword, int limit) {
        String kw = blankToNull(keyword);
        if (kw == null) {
            SearchResultDto empty = new SearchResultDto();
            empty.setNotes(List.of());
            empty.setLife(List.of());
            empty.setNoteTotal(0);
            empty.setLifeTotal(0);
            return empty;
        }

        String statusFilter = adminGuard.isCurrentAdmin() ? null : ContentStatus.PUBLISHED;
        int safeLimit = Math.min(50, Math.max(1, limit));

        long noteTotal = noteMapper.countList(null, kw, statusFilter, null, null);
        long lifeTotal = lifeMapper.countList(kw, statusFilter, null, null);

        List<NoteDto> notes = noteMapper
                .selectList(null, kw, statusFilter, null, null, "date_desc", 0, safeLimit)
                .stream()
                .map(this::toNoteDto)
                .toList();
        List<LifeDto> life = lifeMapper
                .selectList(kw, statusFilter, null, null, "date_desc", 0, safeLimit)
                .stream()
                .map(this::toLifeDto)
                .toList();

        SearchResultDto result = new SearchResultDto();
        result.setNotes(notes);
        result.setLife(life);
        result.setNoteTotal(noteTotal);
        result.setLifeTotal(lifeTotal);
        return result;
    }

    private NoteDto toNoteDto(NoteEntity entity) {
        NoteDto dto = new NoteDto();
        dto.setId(entity.getId());
        dto.setTitle(entity.getTitle());
        dto.setExcerpt(entity.getExcerpt());
        dto.setTag(entity.getTag());
        dto.setTopicId(entity.getTopicId());
        dto.setContent(entity.getContent());
        dto.setDate(entity.getDate());
        dto.setImages(JsonUtil.fromJson(entity.getImagesJson()));
        dto.setViewCount(contentViewCache.getDisplayCount("note", entity.getId(), entity.getViewCount()));
        dto.setPinned(entity.isPinned());
        dto.setStatus(entity.getStatus() != null ? entity.getStatus() : ContentStatus.PUBLISHED);
        dto.setAgentReply(AgentReplySupport.presentForNote(agentReplyProperties, entity.getAgentReply()));
        dto.setAgentReplyStatus(
                entity.getAgentReplyStatus() != null ? entity.getAgentReplyStatus() : "none");
        return dto;
    }

    private LifeDto toLifeDto(LifeEntity entity) {
        LifeDto dto = new LifeDto();
        dto.setId(entity.getId());
        dto.setTitle(entity.getTitle());
        dto.setExcerpt(entity.getExcerpt());
        dto.setTag(entity.getTag());
        dto.setContent(entity.getContent());
        dto.setDate(entity.getDate());
        dto.setImages(JsonUtil.fromJson(entity.getImagesJson()));
        dto.setViewCount(contentViewCache.getDisplayCount("life", entity.getId(), entity.getViewCount()));
        dto.setPinned(entity.isPinned());
        dto.setStatus(entity.getStatus() != null ? entity.getStatus() : ContentStatus.PUBLISHED);
        dto.setAgentReply(AgentReplySupport.presentForLife(agentReplyProperties, entity.getAgentReply()));
        return dto;
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value;
    }
}
