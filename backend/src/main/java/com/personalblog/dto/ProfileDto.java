package com.personalblog.dto;

import lombok.Data;

import java.util.List;

@Data
public class ProfileDto {
  /** 资料所属用户 id，便于后续多用户扩展 */
  private Long userId;
  private String name;
  private String subtitle;
  private String bio;
  private List<String> focus;
  private String avatarUrl;
  /** 是否为站点公开展示的主人资料 */
  private Boolean siteOwner;
}
