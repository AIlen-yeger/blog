package com.personalblog.service;

import com.personalblog.dto.MusicAllPlayRankDto;
import com.personalblog.dto.MusicWeeklyPlayRankDto;

import java.util.List;

/** Agent / Python 侧查询音乐统计（近一周播放排行等）。 */
public interface AgentMusicQueryService {

    /**
     * 当前登录用户近 {@code app.music.weekly-window-days} 天播放排行（已按次数降序）。
     */
    List<MusicWeeklyPlayRankDto> listWeeklyPlaysForCurrentUser();

    /**
     * 当前登录用户库内累计播放排行（play_count &gt; 0，已按次数降序，条数受配置限制）。
     */
    List<MusicAllPlayRankDto> listAllPlaysForCurrentUser();
}
