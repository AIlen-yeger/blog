package com.personalblog.controller;

import com.personalblog.common.ApiResponse;
import com.personalblog.dto.SearchResultDto;
import com.personalblog.service.ContentSearchService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/search")
@RequiredArgsConstructor
public class SearchController {

    private final ContentSearchService contentSearchService;

    @GetMapping
    public ApiResponse<SearchResultDto> search(
            @RequestParam String q,
            @RequestParam(defaultValue = "30") int limit) {
        return ApiResponse.ok(contentSearchService.search(q, limit));
    }
}
