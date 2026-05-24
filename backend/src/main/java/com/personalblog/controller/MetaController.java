package com.personalblog.controller;

import com.personalblog.common.ApiResponse;
import com.personalblog.dto.ArchiveMonthDto;
import com.personalblog.dto.TagCountDto;
import com.personalblog.service.ContentMetaService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/meta")
@RequiredArgsConstructor
public class MetaController {

    private final ContentMetaService contentMetaService;

    @GetMapping("/tags")
    public ApiResponse<List<TagCountDto>> listTags() {
        return ApiResponse.ok(contentMetaService.listTags());
    }

    @GetMapping("/archive-months")
    public ApiResponse<List<ArchiveMonthDto>> listArchiveMonths() {
        return ApiResponse.ok(contentMetaService.listArchiveMonths());
    }
}
