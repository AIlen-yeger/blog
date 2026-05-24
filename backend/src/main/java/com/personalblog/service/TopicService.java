package com.personalblog.service;

import com.personalblog.dto.TopicDto;

import java.util.List;

public interface TopicService {

    List<TopicDto> listTopics();

    /** 按名称查找专题，不存在则创建并返回 */
    TopicDto findOrCreateByTitle(String title);
}
