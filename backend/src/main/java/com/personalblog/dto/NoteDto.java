package com.personalblog.dto;

import lombok.Data;

import java.util.List;

@Data
public class NoteDto {
    private String id;
    private String title;
    private String excerpt;
    private String tag;
    private String topicId;
    private String content;
    private String date;
    private List<String> images;
    private int viewCount;
    private boolean pinned;
    private String status;
}
