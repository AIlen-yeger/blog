package com.personalblog.controller;

import com.personalblog.common.ApiResponse;
import com.personalblog.dto.MusicTrackDto;
import com.personalblog.dto.MusicTrackWriteRequest;
import com.personalblog.dto.QqMusicParseResultDto;
import com.personalblog.service.UserMusicTrackService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/music")
@RequiredArgsConstructor
public class MusicTrackController {

    private final UserMusicTrackService userMusicTrackService;

    /** 着陆页 / 游客：站点主人的公开播放列表 */
    @GetMapping("/site-owner")
    public ApiResponse<List<MusicTrackDto>> siteOwnerTracks() {
        return ApiResponse.ok(userMusicTrackService.listSiteOwnerTracks());
    }

    /** 当前登录用户播放列表 */
    @GetMapping("/me")
    public ApiResponse<List<MusicTrackDto>> myTracks() {
        return ApiResponse.ok(userMusicTrackService.listForCurrentUser());
    }

    @GetMapping("/users/{userId}")
    public ApiResponse<List<MusicTrackDto>> userTracks(@PathVariable long userId) {
        return ApiResponse.ok(userMusicTrackService.listForUser(userId));
    }

    /** 仅解析分享链接中的 songid（不落库），供前端预览或 Agent 调试 */
    @PostMapping("/parse")
    public ApiResponse<QqMusicParseResultDto> parseShareUrl(@RequestBody Map<String, String> body) {
        String shareUrl = body == null ? null : body.get("shareUrl");
        return ApiResponse.ok(userMusicTrackService.parseShareUrl(shareUrl));
    }

    /** 添加 QQ 曲目（需登录；Agent 工具后续调此接口） */
    @PostMapping("/tracks")
    public ApiResponse<MusicTrackDto> addTrack(@RequestBody MusicTrackWriteRequest request) {
        return ApiResponse.ok(userMusicTrackService.addTrackForCurrentUser(request));
    }

    @DeleteMapping("/tracks/{id}")
    public ApiResponse<Void> deleteTrack(@PathVariable String id) {
        userMusicTrackService.deleteTrackForCurrentUser(id);
        return ApiResponse.ok(null);
    }

    /** 记录一次播放（公开，用于着陆页 / 关于页统计） */
    @PostMapping("/tracks/{id}/play")
    public ApiResponse<MusicTrackDto> recordPlay(@PathVariable String id) {
        return ApiResponse.ok(userMusicTrackService.recordPlay(id));
    }
}
