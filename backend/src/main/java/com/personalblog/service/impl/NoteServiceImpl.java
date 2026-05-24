package com.personalblog.service.impl;

import com.personalblog.common.BusinessException;
import com.personalblog.common.ContentStatus;
import com.personalblog.common.ErrorCode;
import com.personalblog.common.PageResult;
import com.personalblog.dto.NoteDto;
import com.personalblog.dto.NoteWriteRequest;
import com.personalblog.entity.NoteEntity;
import com.personalblog.entity.TopicEntity;
import com.personalblog.cache.ContentViewCache;
import com.personalblog.mapper.ContentViewMapper;
import com.personalblog.mapper.NoteMapper;
import com.personalblog.mapper.TopicMapper;
import com.personalblog.security.AdminGuard;
import com.personalblog.service.NoteService;
import com.personalblog.service.TopicService;
import com.personalblog.util.ExcerptUtil;
import com.personalblog.util.IdGenerator;
import com.personalblog.util.JsonUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

@Service
@RequiredArgsConstructor
public class NoteServiceImpl implements NoteService {

    private final NoteMapper noteMapper;
    private final TopicMapper topicMapper;
    private final TopicService topicService;
    private final ContentViewMapper contentViewMapper;
    private final ContentViewCache contentViewCache;
    private final AdminGuard adminGuard;

    @Override
    public PageResult<NoteDto> listNotes(
            String topicId,
            String keyword,
            String status,
            String tag,
            String yearMonth,
            int page,
            int pageSize,
            String sort) {
        int safePage = Math.max(1, page);
        int safeSize = Math.min(50, Math.max(1, pageSize));
        int offset = (safePage - 1) * safeSize;

        String topicFilter = blankToNull(topicId);
        String keywordFilter = blankToNull(keyword);
        String statusFilter = resolveListStatus(status);
        String tagFilter = blankToNull(tag);
        String monthFilter = blankToNull(yearMonth);
        String sortKey = sort != null ? sort : "date_desc";

        long total = noteMapper.countList(topicFilter, keywordFilter, statusFilter, tagFilter, monthFilter);
        List<NoteDto> list = noteMapper.selectList(
                        topicFilter, keywordFilter, statusFilter, tagFilter, monthFilter, sortKey, offset, safeSize)
                .stream().map(this::toDto).toList();

        return new PageResult<>(list, total, safePage, safeSize);
    }

    @Override
    public NoteDto getNote(String id) {
        NoteEntity entity = noteMapper.selectById(id);
        assertReadable(entity);
        return toDto(entity);
    }

    @Override
    @Transactional
    public NoteDto createNote(NoteWriteRequest request) {
        adminGuard.requireAdmin();
        validateWriteRequest(request, true);

        NoteEntity entity = new NoteEntity();
        entity.setId(IdGenerator.noteId());
        applyWrite(entity, request);
        entity.setDate(LocalDate.now().format(DateTimeFormatter.ISO_LOCAL_DATE));
        ensureStatus(entity);
        noteMapper.insert(entity);
        return toDto(entity);
    }

    @Override
    @Transactional
    public NoteDto updateNote(String id, NoteWriteRequest request) {
        adminGuard.requireAdmin();
        NoteEntity entity = noteMapper.selectById(id);
        if (entity == null) {
            throw new BusinessException(ErrorCode.NOTE_NOT_FOUND);
        }
        validateWriteRequest(request, false);
        applyWrite(entity, request);
        ensureStatus(entity);
        noteMapper.update(entity);
        return toDto(entity);
    }

    @Override
    @Transactional
    public void deleteNote(String id) {
        adminGuard.requireAdmin();
        if (noteMapper.countById(id) == 0) {
            throw new BusinessException(ErrorCode.NOTE_NOT_FOUND);
        }
        contentViewMapper.deleteByContent("note", id);
        noteMapper.deleteById(id);
    }

    @Override
    @Transactional
    public NoteDto pinNote(String id) {
        adminGuard.requireAdmin();
        NoteEntity entity = noteMapper.selectById(id);
        if (entity == null) {
            throw new BusinessException(ErrorCode.NOTE_NOT_FOUND);
        }
        boolean nextPinned = !entity.isPinned();
        if (nextPinned) {
            noteMapper.clearAllPinned();
        }
        noteMapper.updatePinned(id, nextPinned);
        entity = noteMapper.selectById(id);
        return toDto(entity);
    }

    private void validateWriteRequest(NoteWriteRequest request, boolean create) {
        if (create && (request.getTitle() == null || request.getTitle().isBlank())) {
            throw new BusinessException(ErrorCode.TITLE_REQUIRED);
        }
        if (create && blankToNull(request.getTopicId()) == null
                && blankToNull(request.getTopicTitle()) == null) {
            throw new BusinessException(ErrorCode.TOPIC_NOT_FOUND);
        }
    }

    /** 优先 topicId；否则按 topicTitle 查找或自动创建专题 */
    private String resolveTopicId(NoteWriteRequest request) {
        String topicId = blankToNull(request.getTopicId());
        if (topicId != null && topicMapper.countById(topicId) > 0) {
            return topicId;
        }
        String title = blankToNull(request.getTopicTitle());
        if (title == null && topicId != null) {
            TopicEntity byTitle = topicMapper.selectByTitleIgnoreCase(topicId);
            if (byTitle != null) {
                return byTitle.getId();
            }
            title = topicId;
        }
        if (title == null) {
            return null;
        }
        return topicService.findOrCreateByTitle(title).getId();
    }

    private void applyWrite(NoteEntity entity, NoteWriteRequest request) {
        if (request.getTitle() != null && !request.getTitle().isBlank()) {
            entity.setTitle(request.getTitle().trim());
        }
        if (request.getTag() != null && !request.getTag().isBlank()) {
            entity.setTag(request.getTag().trim());
        } else if (entity.getTag() == null) {
            entity.setTag("笔记");
        }
        if (request.getTopicId() != null || request.getTopicTitle() != null) {
            String resolved = resolveTopicId(request);
            if (resolved != null) {
                entity.setTopicId(resolved);
            }
        }
        if (request.getContent() != null) {
            entity.setContent(request.getContent());
        } else if (entity.getContent() == null) {
            entity.setContent("");
        }
        entity.setExcerpt(ExcerptUtil.fromContent(request.getExcerpt(), entity.getContent()));
        if (request.getImages() != null) {
            entity.setImagesJson(JsonUtil.toJson(sanitizeImages(request.getImages())));
        } else if (entity.getImagesJson() == null) {
            entity.setImagesJson("[]");
        }
        if (request.getStatus() != null && !request.getStatus().isBlank()) {
            entity.setStatus(ContentStatus.normalize(request.getStatus()));
        }
    }

    private String resolveListStatus(String requestedStatus) {
        if (adminGuard.isCurrentAdmin()) {
            return blankToNull(requestedStatus);
        }
        return ContentStatus.PUBLISHED;
    }

    private void assertReadable(NoteEntity entity) {
        if (entity == null) {
            throw new BusinessException(ErrorCode.NOTE_NOT_FOUND);
        }
        if (!adminGuard.isCurrentAdmin() && ContentStatus.DRAFT.equals(entity.getStatus())) {
            throw new BusinessException(ErrorCode.NOTE_NOT_FOUND);
        }
    }

    private void ensureStatus(NoteEntity entity) {
        if (entity.getStatus() == null || entity.getStatus().isBlank()) {
            entity.setStatus(ContentStatus.PUBLISHED);
        } else {
            entity.setStatus(ContentStatus.normalize(entity.getStatus()));
        }
    }

    private List<String> sanitizeImages(List<String> images) {
        if (images == null) {
            return List.of();
        }
        List<String> out = new ArrayList<>();
        for (String url : images) {
            if (url == null || url.isBlank()) {
                continue;
            }
            String trimmed = url.trim();
            if (trimmed.length() > 512) {
                trimmed = trimmed.substring(0, 512);
            }
            out.add(trimmed);
            if (out.size() >= 12) {
                break;
            }
        }
        return out;
    }

    private NoteDto toDto(NoteEntity entity) {
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
        return dto;
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value;
    }
}
