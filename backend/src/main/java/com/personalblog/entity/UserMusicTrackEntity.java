package com.personalblog.entity;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class UserMusicTrackEntity {
    private String id;
    private Long userId;
    private String qqSongId;
    private String title;
    private String artist;
    private String src;
    private Integer durationSec;
    private String sourceUrl;
    private Integer sortOrder;
    private Integer playCount;
    private LocalDateTime createdAt;
}
