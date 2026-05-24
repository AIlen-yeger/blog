package com.personalblog.mapper;

import com.personalblog.entity.ProfileEntity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface ProfileMapper {

    ProfileEntity selectById(@Param("id") Long id);

    int insert(ProfileEntity profile);

    int update(ProfileEntity profile);
}
