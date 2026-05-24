package com.personalblog.dto;

import lombok.Data;

import java.util.List;

@Data
public class LifeWriteRequest {
    private String title;
    private String excerpt;
    private String tag;
    private String content;
    private List<String> images;
    /** published | draft */
    private String status;
}
