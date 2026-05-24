package com.personalblog.mapper;

import com.personalblog.entity.TopicEntity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface TopicMapper {

    List<TopicEntity> selectAll();

    TopicEntity selectById(@Param("id") String id);

    int countById(@Param("id") String id);

    TopicEntity selectByTitleIgnoreCase(@Param("title") String title);

    int insert(TopicEntity topic);
}
