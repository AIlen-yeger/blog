package com.personalblog.service.impl;

import com.personalblog.common.BusinessException;
import com.personalblog.common.ErrorCode;
import com.personalblog.dto.CheckInBoardDto;
import com.personalblog.entity.ProfileEntity;
import com.personalblog.entity.UserEntity;
import com.personalblog.mapper.ProfileMapper;
import com.personalblog.mapper.UserCheckInMapper;
import com.personalblog.mapper.UserMapper;
import com.personalblog.security.AdminGuard;
import com.personalblog.security.AuthUserPrincipal;
import com.personalblog.service.UserCheckInService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

@Service
@RequiredArgsConstructor
public class UserCheckInServiceImpl implements UserCheckInService {

    /** 与前端 LANDING_CHECKIN_WEEKS 一致 */
    private static final int BOARD_WEEKS = 12;

    private final UserCheckInMapper userCheckInMapper;
    private final ProfileMapper profileMapper;
    private final UserMapper userMapper;
    private final AdminGuard adminGuard;

    @Override
    public CheckInBoardDto getSiteOwnerBoard() {
        Long userId = resolveSiteOwnerUserId();
        if (userId == null) {
            return emptyBoard();
        }
        return buildBoard(userId);
    }

    @Override
    @Transactional
    public CheckInBoardDto checkInTodayForCurrentUser() {
        AuthUserPrincipal principal = requirePrincipal();
        long userId = resolveUserId(principal);
        return recordToday(userId);
    }

    @Override
    public CheckInBoardDto getBoardForCurrentUser() {
        AuthUserPrincipal principal = requirePrincipal();
        long userId = resolveUserId(principal);
        return buildBoard(userId);
    }

    @Override
    public CheckInBoardDto getBoardForUser(long userId) {
        if (userId <= 0) {
            throw new BusinessException(ErrorCode.TITLE_REQUIRED, "用户无效");
        }
        AuthUserPrincipal principal = requirePrincipal();
        long currentId = resolveUserId(principal);
        if (!adminGuard.isCurrentAdmin() && currentId != userId) {
            throw new BusinessException(ErrorCode.FORBIDDEN);
        }
        return buildBoard(userId);
    }

    private long resolveUserId(AuthUserPrincipal principal) {
        UserEntity user = userMapper.selectByEmail(principal.getEmail());
        if (user == null || user.getId() == null) {
            throw new BusinessException(ErrorCode.UNAUTHORIZED, "用户不存在");
        }
        return user.getId();
    }

    private CheckInBoardDto recordToday(long userId) {
        LocalDate today = LocalDate.now();
        userCheckInMapper.insertIgnore(userId, today);
        return buildBoard(userId);
    }

    /**
     * 着陆页公开展示的用户：profile.site_owner=1；未配置时回退到 admin 账号。
     */
    private Long resolveSiteOwnerUserId() {
        ProfileEntity flagged = profileMapper.selectSiteOwner();
        if (flagged != null && flagged.getUserId() != null) {
            return flagged.getUserId();
        }
        UserEntity admin = userMapper.selectFirstByRole("admin");
        if (admin != null && admin.getId() != null) {
            return admin.getId();
        }
        return null;
    }

    private CheckInBoardDto emptyBoard() {
        CheckInBoardDto empty = new CheckInBoardDto();
        empty.setUserId(0L);
        empty.setTotalDays(0);
        empty.setCheckedInToday(false);
        empty.setDates(List.of());
        return empty;
    }

    private CheckInBoardDto buildBoard(long userId) {
        LocalDate today = LocalDate.now();
        LocalDate since = today.minusDays((long) BOARD_WEEKS * 7 - 1);
        List<String> dates = userCheckInMapper.selectDatesByUserIdSince(userId, since);
        Set<String> dateSet = new HashSet<>(dates);

        CheckInBoardDto dto = new CheckInBoardDto();
        dto.setUserId(userId);
        dto.setTotalDays(userCheckInMapper.countByUserId(userId));
        dto.setCheckedInToday(dateSet.contains(today.toString())
                || userCheckInMapper.existsByUserIdAndDate(userId, today) > 0);
        dto.setDates(dates);
        return dto;
    }

    private AuthUserPrincipal requirePrincipal() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !(authentication.getPrincipal() instanceof AuthUserPrincipal principal)) {
            throw new BusinessException(ErrorCode.UNAUTHORIZED);
        }
        return principal;
    }
}
