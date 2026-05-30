package com.personalblog.service.impl;

import com.personalblog.common.BusinessException;
import com.personalblog.common.ErrorCode;
import com.personalblog.dto.MusicTrackDto;
import com.personalblog.dto.MusicTrackWriteRequest;
import com.personalblog.dto.QqMusicParseResultDto;
import com.personalblog.entity.ProfileEntity;
import com.personalblog.entity.UserEntity;
import com.personalblog.entity.UserMusicTrackEntity;
import com.personalblog.cache.MusicWeeklyPlayCache;
import com.personalblog.mapper.ProfileMapper;
import com.personalblog.mapper.UserMapper;
import com.personalblog.mapper.UserMusicTrackMapper;
import com.personalblog.security.AdminGuard;
import com.personalblog.security.AuthUserPrincipal;
import com.personalblog.service.UserMusicTrackService;
import com.personalblog.util.IdGenerator;
import com.personalblog.util.QqMusicUrlParser;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
public class UserMusicTrackServiceImpl implements UserMusicTrackService {

    private final UserMusicTrackMapper userMusicTrackMapper;
    private final ProfileMapper profileMapper;
    private final UserMapper userMapper;
    private final AdminGuard adminGuard;
    private final MusicWeeklyPlayCache musicWeeklyPlayCache;

    @Override
    public List<MusicTrackDto> listSiteOwnerTracks() {
        Long userId = resolveSiteOwnerUserId();
        if (userId == null) {
            return List.of();
        }
        return listForUserInternal(userId);
    }

    @Override
    public List<MusicTrackDto> listForCurrentUser() {
        return listForUserInternal(resolveCurrentUserId());
    }

    @Override
    public List<MusicTrackDto> listForUser(long userId) {
        if (userId <= 0) {
            throw new BusinessException(ErrorCode.TITLE_REQUIRED, "用户无效");
        }
        long currentId = resolveCurrentUserId();
        if (!adminGuard.isCurrentAdmin() && currentId != userId) {
            throw new BusinessException(ErrorCode.FORBIDDEN);
        }
        return listForUserInternal(userId);
    }

    @Override
    public QqMusicParseResultDto parseShareUrl(String shareUrl) {
        String trimmed = shareUrl == null ? "" : shareUrl.trim();
        String songId = QqMusicUrlParser.parseSongId(trimmed)
                .orElseThrow(() -> new BusinessException(ErrorCode.INVALID_QQ_MUSIC_URL));
        return QqMusicParseResultDto.builder()
                .qqSongId(songId)
                .shareUrl(trimmed)
                .build();
    }

    @Override
    @Transactional
    public MusicTrackDto addTrackForCurrentUser(MusicTrackWriteRequest request) {
        if (request == null) {
            throw new BusinessException(ErrorCode.TITLE_REQUIRED, "请求体不能为空");
        }
        long userId = resolveCurrentUserId();

        String shareUrl = trimToNull(request.getShareUrl());
        String qqSongId = trimToNull(request.getQqSongId());
        if (qqSongId == null && shareUrl != null) {
            qqSongId = QqMusicUrlParser.parseSongId(shareUrl)
                    .orElseThrow(() -> new BusinessException(ErrorCode.INVALID_QQ_MUSIC_URL));
        }
        if (qqSongId == null) {
            throw new BusinessException(ErrorCode.INVALID_QQ_MUSIC_URL, "请提供 QQ 音乐分享链接或 songid");
        }

        if (userMusicTrackMapper.countByUserIdAndQqSongId(userId, qqSongId) > 0) {
            throw new BusinessException(ErrorCode.MUSIC_TRACK_EXISTS);
        }

        String title = trimToNull(request.getTitle());
        if (title == null) {
            title = "QQ 音乐 #" + qqSongId;
        }
        String artist = nullToEmpty(request.getArtist());
        String src = nullToEmpty(request.getSrc());

        int nextSort = userMusicTrackMapper.selectMaxSortOrder(userId) + 1;

        UserMusicTrackEntity entity = new UserMusicTrackEntity();
        entity.setId(IdGenerator.musicTrackId());
        entity.setUserId(userId);
        entity.setQqSongId(qqSongId);
        entity.setTitle(title);
        entity.setArtist(artist);
        entity.setSrc(src);
        entity.setDurationSec(request.getDurationSec());
        entity.setSourceUrl(shareUrl);
        entity.setSortOrder(nextSort);
        entity.setPlayCount(0);

        userMusicTrackMapper.insert(entity);
        return toDto(entity);
    }

    @Override
    @Transactional
    public void deleteTrackForCurrentUser(String trackId) {
        if (trackId == null || trackId.isBlank()) {
            throw new BusinessException(ErrorCode.TITLE_REQUIRED, "曲目 ID 无效");
        }
        long userId = resolveCurrentUserId();
        int rows = userMusicTrackMapper.deleteByIdAndUserId(trackId.trim(), userId);
        if (rows == 0) {
            throw new BusinessException(ErrorCode.NOTE_NOT_FOUND, "曲目不存在或无权删除");
        }
    }

    @Override
    @Transactional
    public MusicTrackDto recordPlay(String trackId) {
        if (trackId == null || trackId.isBlank()) {
            throw new BusinessException(ErrorCode.TITLE_REQUIRED, "曲目 ID 无效");
        }
        String id = trackId.trim();
        UserMusicTrackEntity existing = userMusicTrackMapper.selectById(id);
        if (existing == null) {
            throw new BusinessException(ErrorCode.NOTE_NOT_FOUND, "曲目不存在");
        }
        userMusicTrackMapper.incrementPlayCount(id);
        if (existing.getUserId() != null) {
            musicWeeklyPlayCache.recordPlay(existing.getUserId(), id);
        }
        UserMusicTrackEntity updated = userMusicTrackMapper.selectById(id);
        return toDto(updated != null ? updated : existing);
    }

    private List<MusicTrackDto> listForUserInternal(long userId) {
        return userMusicTrackMapper.selectByUserId(userId).stream()
                .map(this::toDto)
                .toList();
    }

    private MusicTrackDto toDto(UserMusicTrackEntity entity) {
        return MusicTrackDto.builder()
                .id(entity.getId())
                .title(entity.getTitle())
                .artist(entity.getArtist())
                .qqSongId(entity.getQqSongId())
                .durationSec(entity.getDurationSec())
                .playCount(entity.getPlayCount() != null ? entity.getPlayCount() : 0)
                .build();
    }

    private Long resolveSiteOwnerUserId() {
        ProfileEntity profile = profileMapper.selectSiteOwner();
        return profile == null ? null : profile.getUserId();
    }

    private long resolveCurrentUserId() {
        AuthUserPrincipal principal = requirePrincipal();
        UserEntity user = userMapper.selectByEmail(principal.getEmail());
        if (user == null || user.getId() == null) {
            throw new BusinessException(ErrorCode.UNAUTHORIZED, "用户不存在");
        }
        return user.getId();
    }

    private AuthUserPrincipal requirePrincipal() {
        var auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || !(auth.getPrincipal() instanceof AuthUserPrincipal principal)) {
            throw new BusinessException(ErrorCode.UNAUTHORIZED);
        }
        return principal;
    }

    private static String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }

    private static String nullToEmpty(String value) {
        return value == null ? "" : value.trim();
    }
}
