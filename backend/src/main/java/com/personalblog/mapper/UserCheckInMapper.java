package com.personalblog.mapper;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDate;
import java.util.List;

@Mapper
public interface UserCheckInMapper {

    int insertIgnore(@Param("userId") Long userId, @Param("checkInDate") LocalDate checkInDate);

    int countByUserId(@Param("userId") Long userId);

    int existsByUserIdAndDate(@Param("userId") Long userId, @Param("checkInDate") LocalDate checkInDate);

    List<String> selectDatesByUserIdSince(
            @Param("userId") Long userId,
            @Param("since") LocalDate since);
}
