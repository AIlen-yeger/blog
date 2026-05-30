package com.personalblog.service;

import com.personalblog.dto.CheckInBoardDto;

public interface UserCheckInService {

    /** 站点主人（着陆页展示）的签到板 */
    CheckInBoardDto getSiteOwnerBoard();

    /** 当前登录用户今日签到 */
    CheckInBoardDto checkInTodayForCurrentUser();

    /** 当前登录用户签到板（只读，不写入） */
    CheckInBoardDto getBoardForCurrentUser();

    /** 指定用户的签到板（本人或管理员） */
    CheckInBoardDto getBoardForUser(long userId);
}
