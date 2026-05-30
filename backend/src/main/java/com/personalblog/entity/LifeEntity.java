package com.personalblog.entity;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class LifeEntity {

    private String id;
    private String title;
    private String excerpt;
    private String tag = "生活";
    private String content;
    private String date;
    private String imagesJson;
    private int viewCount;
    private boolean pinned;
    private String status = "published";
    /** Kohaku 自动回复全文 */
    private String agentReply;
}
