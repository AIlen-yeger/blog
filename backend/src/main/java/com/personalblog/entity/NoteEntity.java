package com.personalblog.entity;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class NoteEntity {

    private String id;
    private String title;
    private String excerpt;
    private String tag = "笔记";
    private String topicId;
    private String content;
    private String date;
    /** JSON 数组，图片 URL 列表 */
    private String imagesJson;
    private int viewCount;
    private boolean pinned;
    private String status = "published";
}
