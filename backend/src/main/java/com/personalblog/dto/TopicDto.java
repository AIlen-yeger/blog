package com.personalblog.dto;

import lombok.Data;

@Data
public class TopicDto {
    private String id;
    private String title;
    private String excerpt;
    private String tag;
    private String date;
    private Long noteCount;
}
