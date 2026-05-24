package com.personalblog.entity;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class TopicEntity {

    private String id;
    private String title;
    private String excerpt;
    private String tag = "专题";
    private String date;
}
