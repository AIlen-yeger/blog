package com.personalblog.service;

import com.personalblog.dto.AvatarUploadResultDto;
import com.personalblog.dto.ProfileDto;
import com.personalblog.dto.ProfileUpdateRequest;
import com.personalblog.entity.UserEntity;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;

public interface ProfileService {

    /** 站点着陆页公开展示的主人资料 */
    ProfileDto getSitePublicProfile();

    /** 指定用户的公开资料（后续多用户主页扩展） */
    ProfileDto getProfileByUserId(Long userId);

    /** 当前登录用户自己的资料 */
    ProfileDto getCurrentUserProfile();

    ProfileDto updateCurrentUserProfile(ProfileUpdateRequest request);

    AvatarUploadResultDto uploadAvatar(MultipartFile file) throws IOException;

    /** 注册或首次访问时为用户创建默认资料 */
    void ensureProfileForUser(UserEntity user);
}
