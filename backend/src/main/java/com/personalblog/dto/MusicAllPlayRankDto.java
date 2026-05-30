package com.personalblog.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class MusicAllPlayRankDto {
    private String title;
    private String artist;
    /** 数据库累计播放次数（user_music_track.play_count） */
    private int playCount;
}
