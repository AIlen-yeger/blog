package com.personalblog.service.impl;

import com.personalblog.dto.TimelineDto;
import com.personalblog.entity.TimelineEntity;
import com.personalblog.mapper.TimelineMapper;
import com.personalblog.security.AdminGuard;
import com.personalblog.service.TimelineService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class TimelineServiceImpl implements TimelineService {

    private final TimelineMapper timelineMapper;
    private final AdminGuard adminGuard;

    @Override
    public List<TimelineDto> listTimeline() {
        return timelineMapper.selectAll().stream().map(this::toDto).toList();
    }

    private TimelineDto toDto(TimelineEntity entity) {
        TimelineDto dto = new TimelineDto();
        dto.setId(entity.getId());
        dto.setPeriod(entity.getPeriod());
        dto.setTitle(entity.getTitle());
        dto.setDesc(entity.getDesc());
        return dto;
    }
}
