package com.personalblog.service.impl;

import com.personalblog.dto.TopicDto;
import com.personalblog.entity.TopicEntity;
import com.personalblog.util.IdGenerator;
import com.personalblog.mapper.NoteMapper;
import com.personalblog.mapper.TopicMapper;
import com.personalblog.security.AdminGuard;
import com.personalblog.service.TopicService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.List;

@Service
@RequiredArgsConstructor
public class TopicServiceImpl implements TopicService {

    private final TopicMapper topicMapper;
    private final NoteMapper noteMapper;
    private final AdminGuard adminGuard;

    @Override
    public List<TopicDto> listTopics() {
        return topicMapper.selectAll().stream().map(this::toDto).toList();
    }

    @Override
    @Transactional
    public TopicDto findOrCreateByTitle(String title) {
        adminGuard.requireAdmin();
        String trimmed = title != null ? title.trim() : "";
        if (trimmed.isEmpty()) {
            throw new com.personalblog.common.BusinessException(
                    com.personalblog.common.ErrorCode.TOPIC_NOT_FOUND);
        }
        TopicEntity existing = topicMapper.selectByTitleIgnoreCase(trimmed);
        if (existing != null) {
            return toDto(existing);
        }
        TopicEntity topic = new TopicEntity();
        topic.setId(IdGenerator.topicId());
        topic.setTitle(trimmed);
        topic.setExcerpt(trimmed.length() > 48 ? trimmed.substring(0, 48) + "…" : trimmed);
        topic.setTag("专题");
        topic.setDate(LocalDate.now().format(DateTimeFormatter.ISO_LOCAL_DATE));
        topicMapper.insert(topic);
        return toDto(topic);
    }

    private TopicDto toDto(TopicEntity entity) {
        TopicDto dto = new TopicDto();
        dto.setId(entity.getId());
        dto.setTitle(entity.getTitle());
        dto.setExcerpt(entity.getExcerpt());
        dto.setTag(entity.getTag());
        dto.setDate(entity.getDate());
        dto.setNoteCount(noteMapper.countByTopicId(entity.getId()));
        return dto;
    }
}
