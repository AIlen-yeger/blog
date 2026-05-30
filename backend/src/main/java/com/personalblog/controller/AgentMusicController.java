package com.personalblog.controller;

import com.personalblog.common.ApiResponse;
import com.personalblog.dto.MusicAllPlayRankDto;
import com.personalblog.dto.MusicWeeklyPlayRankDto;
import com.personalblog.service.AgentMusicQueryService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 供 Python Agent 调用的音乐数据接口（需登录 JWT）。
 */
@RestController
@RequestMapping("/agent/music")
@RequiredArgsConstructor
public class AgentMusicController {

    private final AgentMusicQueryService agentMusicQueryService;

    /** 近一周播放排行：歌名、歌手、周播放次数（已降序）。 */
    @GetMapping("/weekly-plays")
    public ApiResponse<List<MusicWeeklyPlayRankDto>> weeklyPlays() {
        return ApiResponse.ok(agentMusicQueryService.listWeeklyPlaysForCurrentUser());
    }

    /** 库内累计播放排行：歌名、歌手、play_count（已降序，条数见 app.music.all-plays-top-limit）。 */
    @GetMapping("/all-plays")
    public ApiResponse<List<MusicAllPlayRankDto>> allPlays() {
        return ApiResponse.ok(agentMusicQueryService.listAllPlaysForCurrentUser());
    }
}
