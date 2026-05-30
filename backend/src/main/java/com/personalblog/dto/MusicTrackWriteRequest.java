package com.personalblog.dto;

import lombok.Data;

@Data
public class MusicTrackWriteRequest {
    /** QQ 分享链接或含 songid 的文本 */
    private String shareUrl;
    /** 与 shareUrl 二选一 */
    private String qqSongId;
    private String title;
    private String artist;
    private String src;
    private Integer durationSec;
}
