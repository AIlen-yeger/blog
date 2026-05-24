package com.personalblog.controller;

import com.personalblog.common.ApiResponse;
import com.personalblog.dto.TopicDto;
import com.personalblog.service.TopicService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/topics")
@RequiredArgsConstructor
public class TopicController {

    private final TopicService topicService;

    @GetMapping
    public ApiResponse<List<TopicDto>> listTopics() {
        return ApiResponse.ok(topicService.listTopics());
    }
}
