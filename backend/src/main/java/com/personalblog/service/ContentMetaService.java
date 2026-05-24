package com.personalblog.service;

import com.personalblog.dto.ArchiveMonthDto;
import com.personalblog.dto.TagCountDto;

import java.util.List;

public interface ContentMetaService {

    List<TagCountDto> listTags();

    List<ArchiveMonthDto> listArchiveMonths();
}
