package com.personalblog.mapper;

import com.personalblog.entity.UserEntity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface UserMapper {

    UserEntity selectByEmail(@Param("email") String email);

    int countByEmail(@Param("email") String email);

    int insert(UserEntity user);
}
