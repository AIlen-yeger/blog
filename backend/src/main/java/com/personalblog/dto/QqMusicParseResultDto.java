package com.personalblog.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class QqMusicParseResultDto {
    private String qqSongId;
    private String shareUrl;
}
