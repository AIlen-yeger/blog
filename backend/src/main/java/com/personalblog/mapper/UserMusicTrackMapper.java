package com.personalblog.mapper;

import com.personalblog.entity.UserMusicTrackEntity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface UserMusicTrackMapper {

    List<UserMusicTrackEntity> selectByUserId(@Param("userId") Long userId);

    List<UserMusicTrackEntity> selectTopPlayedByUserId(
            @Param("userId") Long userId,
            @Param("limit") int limit);

    UserMusicTrackEntity selectById(@Param("id") String id);

    int countByUserIdAndQqSongId(@Param("userId") Long userId, @Param("qqSongId") String qqSongId);

    int insert(UserMusicTrackEntity entity);

    int deleteByIdAndUserId(@Param("id") String id, @Param("userId") Long userId);

    int selectMaxSortOrder(@Param("userId") Long userId);

    int incrementPlayCount(@Param("id") String id);
}
