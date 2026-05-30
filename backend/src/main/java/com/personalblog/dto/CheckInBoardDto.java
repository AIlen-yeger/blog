package com.personalblog.dto;

import lombok.Data;

import java.util.List;

@Data
public class CheckInBoardDto {

    private Long userId;
    private int totalDays;
    private boolean checkedInToday;
    /** 已签到日期 yyyy-MM-dd */
    private List<String> dates;
}
