package com.personalblog.service.impl;

import com.personalblog.common.BusinessException;
import com.personalblog.common.ContentStatus;
import com.personalblog.common.ErrorCode;
import com.personalblog.common.PageResult;
import com.personalblog.dto.LifeDto;
import com.personalblog.dto.LifeWriteRequest;
import com.personalblog.entity.LifeEntity;
import com.personalblog.cache.ContentViewCache;
import com.personalblog.config.AgentReplyProperties;
import com.personalblog.mapper.ContentViewMapper;
import com.personalblog.mapper.LifeMapper;
import com.personalblog.security.AdminGuard;
import com.personalblog.service.LifeService;
import com.personalblog.util.AgentReplySupport;
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
public class LifeServiceImpl implements LifeService {

    private final LifeMapper lifeMapper;
    private final ContentViewMapper contentViewMapper;
    private final ContentViewCache contentViewCache;
    private final AdminGuard adminGuard;
    private final AgentReplyProperties agentReplyProperties;

    @Override
    public PageResult<LifeDto> listLife(
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
        String sortKey = sort != null ? sort : "date_desc";
        String keywordFilter = blankToNull(keyword);
        String statusFilter = resolveListStatus(status);
        String tagFilter = blankToNull(tag);
        String monthFilter = blankToNull(yearMonth);

        long total = lifeMapper.countList(keywordFilter, statusFilter, tagFilter, monthFilter);
        List<LifeDto> list = lifeMapper.selectList(
                        keywordFilter, statusFilter, tagFilter, monthFilter, sortKey, offset, safeSize)
                .stream().map(this::toDto).toList();

        return new PageResult<>(list, total, safePage, safeSize);
    }

    @Override
    @Transactional
    public LifeDto createLife(LifeWriteRequest request) {
        adminGuard.requireAdmin();
        if (request.getTitle() == null || request.getTitle().isBlank()) {
            throw new BusinessException(ErrorCode.TITLE_REQUIRED);
        }

        LifeEntity entity = new LifeEntity();
        entity.setId(IdGenerator.lifeId());
        applyWrite(entity, request);
        entity.setDate(LocalDate.now().format(DateTimeFormatter.ISO_LOCAL_DATE));
        ensureStatus(entity);
        lifeMapper.insert(entity);
        return toDto(entity);
    }

    @Override
    @Transactional
    public LifeDto updateLife(String id, LifeWriteRequest request) {
        adminGuard.requireAdmin();
        LifeEntity entity = lifeMapper.selectById(id);
        if (entity == null) {
            throw new BusinessException(ErrorCode.LIFE_NOT_FOUND);
        }
        applyWrite(entity, request);
        ensureStatus(entity);
        lifeMapper.update(entity);
        return toDto(entity);
    }

    @Override
    @Transactional
    public void deleteLife(String id) {
        adminGuard.requireAdmin();
        if (lifeMapper.countById(id) == 0) {
            throw new BusinessException(ErrorCode.LIFE_NOT_FOUND);
        }
        contentViewMapper.deleteByContent("life", id);
        lifeMapper.deleteById(id);
    }

    @Override
    @Transactional
    public LifeDto pinLife(String id) {
        adminGuard.requireAdmin();
        LifeEntity entity = lifeMapper.selectById(id);
        if (entity == null) {
            throw new BusinessException(ErrorCode.LIFE_NOT_FOUND);
        }
        boolean nextPinned = !entity.isPinned();
        if (nextPinned) {
            lifeMapper.clearAllPinned();
        }
        lifeMapper.updatePinned(id, nextPinned);
        entity = lifeMapper.selectById(id);
        return toDto(entity);
    }

    private void applyWrite(LifeEntity entity, LifeWriteRequest request) {
        if (request.getTitle() != null && !request.getTitle().isBlank()) {
            entity.setTitle(request.getTitle().trim());
        }
        if (request.getTag() != null && !request.getTag().isBlank()) {
            entity.setTag(request.getTag().trim());
        } else if (entity.getTag() == null) {
            entity.setTag("生活");
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

    private void ensureStatus(LifeEntity entity) {
        if (entity.getStatus() == null || entity.getStatus().isBlank()) {
            entity.setStatus(ContentStatus.PUBLISHED);
        } else {
            entity.setStatus(ContentStatus.normalize(entity.getStatus()));
        }
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value;
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

    private LifeDto toDto(LifeEntity entity) {
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
}
