package com.personalblog.service.impl;

import com.personalblog.common.ContentStatus;
import com.personalblog.dto.ArchiveMonthDto;
import com.personalblog.dto.TagCountDto;
import com.personalblog.mapper.LifeMapper;
import com.personalblog.mapper.NoteMapper;
import com.personalblog.security.AdminGuard;
import com.personalblog.service.ContentMetaService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class ContentMetaServiceImpl implements ContentMetaService {

    private final NoteMapper noteMapper;
    private final LifeMapper lifeMapper;
    private final AdminGuard adminGuard;

    @Override
    public List<TagCountDto> listTags() {
        String statusFilter = adminGuard.isCurrentAdmin() ? null : ContentStatus.PUBLISHED;
        Map<String, Long> merged = new LinkedHashMap<>();
        for (TagCountDto row : noteMapper.selectTagCounts(statusFilter)) {
            merged.merge(row.getTag(), row.getCount(), Long::sum);
        }
        for (TagCountDto row : lifeMapper.selectTagCounts(statusFilter)) {
            merged.merge(row.getTag(), row.getCount(), Long::sum);
        }
        return merged.entrySet().stream()
                .sorted(Comparator.comparingLong((Map.Entry<String, Long> e) -> e.getValue()).reversed()
                        .thenComparing(Map.Entry::getKey))
                .map(e -> new TagCountDto(e.getKey(), e.getValue()))
                .toList();
    }

    @Override
    public List<ArchiveMonthDto> listArchiveMonths() {
        String statusFilter = adminGuard.isCurrentAdmin() ? null : ContentStatus.PUBLISHED;
        Map<String, Long> merged = new LinkedHashMap<>();
        for (ArchiveMonthDto row : noteMapper.selectArchiveMonths(statusFilter)) {
            merged.merge(row.getMonth(), row.getCount(), Long::sum);
        }
        for (ArchiveMonthDto row : lifeMapper.selectArchiveMonths(statusFilter)) {
            merged.merge(row.getMonth(), row.getCount(), Long::sum);
        }
        List<ArchiveMonthDto> list = new ArrayList<>();
        merged.entrySet().stream()
                .sorted(Comparator.comparing(Map.Entry<String, Long>::getKey).reversed())
                .forEach(e -> list.add(new ArchiveMonthDto(e.getKey(), e.getValue())));
        return list;
    }
}
