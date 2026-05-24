package com.personalblog.dto;

import lombok.Data;

import java.util.List;

@Data
public class LifeDto {
    private String id;
    private String title;
    private String excerpt;
    private String tag;
    private String content;
    private String date;
    private List<String> images;
    private int viewCount;
    private boolean pinned;
    private String status;
}
