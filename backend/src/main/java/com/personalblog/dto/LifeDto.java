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
    /** 为 true 时仅管理员可见 */
    private boolean ownerOnly;
    /** Kohaku 根据正文生成的自动回复 */
    private String agentReply;
}
