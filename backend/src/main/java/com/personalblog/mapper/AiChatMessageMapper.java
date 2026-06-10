package com.personalblog.mapper;

import com.personalblog.entity.AiChatMessageEntity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface AiChatMessageMapper {

    List<AiChatMessageEntity> listBySession(
            @Param("sessionId") String sessionId,
            @Param("userId") Long userId,
            @Param("channel") String channel);

    int deleteBySessionIdAndUserId(
            @Param("sessionId") String sessionId,
            @Param("userId") Long userId,
            @Param("channel") String channel);
}
