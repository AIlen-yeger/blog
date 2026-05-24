package com.personalblog.controller;

import com.personalblog.common.ApiResponse;
import com.personalblog.dto.TimelineDto;
import com.personalblog.service.TimelineService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/timeline")
@RequiredArgsConstructor
public class TimelineController {

    private final TimelineService timelineService;

    @GetMapping
    public ApiResponse<List<TimelineDto>> listTimeline() {
        return ApiResponse.ok(timelineService.listTimeline());
    }
}
