package com.personalblog.mapper;

import com.personalblog.dto.ArchiveMonthDto;
import com.personalblog.dto.TagCountDto;
import com.personalblog.entity.LifeEntity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface LifeMapper {

    LifeEntity selectById(@Param("id") String id);

    int countById(@Param("id") String id);

    long countList(
            @Param("keyword") String keyword,
            @Param("status") String status,
            @Param("tag") String tag,
            @Param("yearMonth") String yearMonth);

    List<LifeEntity> selectList(
            @Param("keyword") String keyword,
            @Param("status") String status,
            @Param("tag") String tag,
            @Param("yearMonth") String yearMonth,
            @Param("sort") String sort,
            @Param("offset") int offset,
            @Param("limit") int limit);

    List<TagCountDto> selectTagCounts(@Param("status") String status);

    List<ArchiveMonthDto> selectArchiveMonths(@Param("status") String status);

    int insert(LifeEntity life);

    int update(LifeEntity life);

    int deleteById(@Param("id") String id);

    int incrementViewCount(@Param("id") String id);

    int incrementViewCountBy(@Param("id") String id, @Param("delta") int delta);

    int selectViewCount(@Param("id") String id);

    int clearAllPinned();

    int updatePinned(@Param("id") String id, @Param("pinned") boolean pinned);
}
