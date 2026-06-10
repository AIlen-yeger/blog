package com.personalblog.entity;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class ProfileEntity {

    private Long id;
    /** 关联 users.id，一人一份资料 */
    private Long userId;
    private String name;
    private String subtitle;
    private String bio;
    private String focusJson;
    private String avatarUrl;
    /** 是否在站点着陆页公开展示（个人博客通常仅一位 site owner） */
    private boolean siteOwner;
    /** Agent 回复是否仅管理员可见（站点级偏好，存于 site owner 资料） */
    private boolean agentReplyOwnerOnly;
}
