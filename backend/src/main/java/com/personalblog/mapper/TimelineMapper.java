package com.personalblog.mapper;

import com.personalblog.entity.TimelineEntity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface TimelineMapper {

    List<TimelineEntity> selectAll();

    int countById(@Param("id") String id);

    int insert(TimelineEntity item);
}
