package com.personalblog.service.impl;

import com.personalblog.cache.MusicWeeklyPlayCache;
import com.personalblog.common.BusinessException;
import com.personalblog.common.ErrorCode;
import com.personalblog.dto.MusicAllPlayRankDto;
import com.personalblog.dto.MusicWeeklyPlayRankDto;
import com.personalblog.entity.UserEntity;
import com.personalblog.entity.UserMusicTrackEntity;
import com.personalblog.mapper.UserMapper;
import com.personalblog.mapper.UserMusicTrackMapper;
import com.personalblog.security.AuthUserPrincipal;
import com.personalblog.service.AgentMusicQueryService;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;

import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class AgentMusicQueryServiceImpl implements AgentMusicQueryService {

    private final MusicWeeklyPlayCache musicWeeklyPlayCache;
    private final UserMusicTrackMapper userMusicTrackMapper;
    private final UserMapper userMapper;

    @Value("${app.music.weekly-window-days:7}")
    private int weeklyWindowDays;

    @Value("${app.music.all-plays-top-limit:30}")
    private int allPlaysTopLimit;

    @Override
    public List<MusicWeeklyPlayRankDto> listWeeklyPlaysForCurrentUser() {
        long userId = resolveCurrentUserId();
        Map<String, Long> counts = musicWeeklyPlayCache.aggregateLastDays(userId, weeklyWindowDays);
        if (counts.isEmpty()) {
            return List.of();
        }

        Map<String, UserMusicTrackEntity> tracksById = userMusicTrackMapper.selectByUserId(userId).stream()
                .collect(Collectors.toMap(UserMusicTrackEntity::getId, t -> t, (a, b) -> a));

        return counts.entrySet().stream()
                .filter(e -> tracksById.containsKey(e.getKey()) && e.getValue() != null && e.getValue() > 0)
                .map(e -> {
                    UserMusicTrackEntity track = tracksById.get(e.getKey());
                    return MusicWeeklyPlayRankDto.builder()
                            .title(track.getTitle())
                            .artist(track.getArtist() != null ? track.getArtist() : "")
                            .weeklyPlayCount(e.getValue().intValue())
                            .build();
                })
                .sorted(Comparator.comparingInt(MusicWeeklyPlayRankDto::getWeeklyPlayCount).reversed())
                .toList();
    }

    @Override
    public List<MusicAllPlayRankDto> listAllPlaysForCurrentUser() {
        long userId = resolveCurrentUserId();
        int limit = allPlaysTopLimit > 0 ? allPlaysTopLimit : 30;
        return userMusicTrackMapper.selectTopPlayedByUserId(userId, limit).stream()
                .map(track -> MusicAllPlayRankDto.builder()
                        .title(track.getTitle())
                        .artist(track.getArtist() != null ? track.getArtist() : "")
                        .playCount(track.getPlayCount() != null ? track.getPlayCount() : 0)
                        .build())
                .toList();
    }

    private long resolveCurrentUserId() {
        var auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || !(auth.getPrincipal() instanceof AuthUserPrincipal principal)) {
            throw new BusinessException(ErrorCode.UNAUTHORIZED);
        }
        UserEntity user = userMapper.selectByEmail(principal.getEmail());
        if (user == null || user.getId() == null) {
            throw new BusinessException(ErrorCode.UNAUTHORIZED, "用户不存在");
        }
        return user.getId();
    }
}
