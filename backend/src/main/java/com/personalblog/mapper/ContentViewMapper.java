package com.personalblog.mapper;

import org.apache.ibatis.annotations.Param;

public interface ContentViewMapper {

    /**
     * 插入浏览记录；若 (content_type, content_id, viewer_key) 已存在则忽略。
     *
     * @return 实际插入行数，1 表示新浏览，0 表示重复
     */
    int insertIgnore(@Param("contentType") String contentType,
                     @Param("contentId") String contentId,
                     @Param("viewerKey") String viewerKey);

    int deleteByContent(@Param("contentType") String contentType,
                        @Param("contentId") String contentId);
}
