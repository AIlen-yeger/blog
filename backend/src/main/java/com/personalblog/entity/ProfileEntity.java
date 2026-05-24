package com.personalblog.entity;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class ProfileEntity {

    private Long id = 1L;
    private String name;
    private String subtitle;
    private String bio;
    private String focusJson;
    private String avatarUrl;
}
