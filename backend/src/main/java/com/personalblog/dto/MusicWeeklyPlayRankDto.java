package com.personalblog.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class MusicWeeklyPlayRankDto {
    private String title;
    private String artist;
    private int weeklyPlayCount;
}
