package com.personalblog.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class MusicTrackDto {
    private String id;
    private String title;
    private String artist;
    private String qqSongId;
    private Integer durationSec;
    private Integer playCount;

}
