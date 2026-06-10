package com.personalblog.mapper;

import com.personalblog.entity.AiChatSessionEntity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface AiChatSessionMapper {

    List<AiChatSessionEntity> listByUserId(@Param("userId") Long userId);

    AiChatSessionEntity selectBySessionIdAndUserId(
            @Param("sessionId") String sessionId,
            @Param("userId") Long userId);

    int insert(AiChatSessionEntity entity);

    int updateTitle(
            @Param("sessionId") String sessionId,
            @Param("userId") Long userId,
            @Param("title") String title);

    int deleteBySessionIdAndUserId(
            @Param("sessionId") String sessionId,
            @Param("userId") Long userId);
}
