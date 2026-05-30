package com.personalblog.controller;

import com.personalblog.common.ApiResponse;
import com.personalblog.dto.CheckInBoardDto;
import com.personalblog.service.UserCheckInService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/check-ins")
@RequiredArgsConstructor
public class CheckInController {

    private final UserCheckInService userCheckInService;

    /** 着陆页展示：站点主人的签到热力图 */
    @GetMapping("/site-owner")
    public ApiResponse<CheckInBoardDto> siteOwnerBoard() {
        return ApiResponse.ok(userCheckInService.getSiteOwnerBoard());
    }

    /** 当前用户今日签到（访问站点时调用） */
    @PostMapping("/today")
    public ApiResponse<CheckInBoardDto> checkInToday() {
        return ApiResponse.ok(userCheckInService.checkInTodayForCurrentUser());
    }

    /** 当前用户签到板（只读） */
    @GetMapping("/me")
    public ApiResponse<CheckInBoardDto> myBoard() {
        return ApiResponse.ok(userCheckInService.getBoardForCurrentUser());
    }

    @GetMapping("/users/{userId}")
    public ApiResponse<CheckInBoardDto> userBoard(@PathVariable long userId) {
        return ApiResponse.ok(userCheckInService.getBoardForUser(userId));
    }
}
