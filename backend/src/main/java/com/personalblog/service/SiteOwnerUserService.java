package com.personalblog.service;

import com.personalblog.entity.ProfileEntity;
import com.personalblog.entity.UserEntity;
import com.personalblog.mapper.ProfileMapper;
import com.personalblog.mapper.UserMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

/**
 * 站点主用户 ID：profile.site_owner=1，未配置时回退 admin。
 */
@Service
@RequiredArgsConstructor
public class SiteOwnerUserService {

    private final ProfileMapper profileMapper;
    private final UserMapper userMapper;

    public long resolveSiteOwnerUserId() {
        ProfileEntity flagged = profileMapper.selectSiteOwner();
        if (flagged != null && flagged.getUserId() != null) {
            return flagged.getUserId();
        }
        UserEntity admin = userMapper.selectFirstByRole("admin");
        if (admin != null && admin.getId() != null) {
            return admin.getId();
        }
        return 0L;
    }
}
