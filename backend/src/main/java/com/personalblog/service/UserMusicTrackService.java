package com.personalblog.service;

import com.personalblog.dto.MusicTrackDto;
import com.personalblog.dto.MusicTrackWriteRequest;
import com.personalblog.dto.QqMusicParseResultDto;

import java.util.List;

public interface UserMusicTrackService {

    List<MusicTrackDto> listSiteOwnerTracks();

    List<MusicTrackDto> listForCurrentUser();

    List<MusicTrackDto> listForUser(long userId);

    QqMusicParseResultDto parseShareUrl(String shareUrl);

    MusicTrackDto addTrackForCurrentUser(MusicTrackWriteRequest request);

    void deleteTrackForCurrentUser(String trackId);

    /** 记录一次播放（公开接口，游客也可为站点主人曲目 +1） */
    MusicTrackDto recordPlay(String trackId);
}
