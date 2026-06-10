package com.personalblog.service.impl;

import com.personalblog.common.BusinessException;
import com.personalblog.common.ErrorCode;
import com.personalblog.dto.AvatarUploadResultDto;
import com.personalblog.dto.ProfileDto;
import com.personalblog.dto.ProfileUpdateRequest;
import com.personalblog.entity.ProfileEntity;
import com.personalblog.entity.UserEntity;
import com.personalblog.entity.UserRole;
import com.personalblog.mapper.ProfileMapper;
import com.personalblog.mapper.UserMapper;
import com.personalblog.security.AdminGuard;
import com.personalblog.security.AuthUserPrincipal;
import com.personalblog.service.ProfileService;
import com.personalblog.util.JsonUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class ProfileServiceImpl implements ProfileService {

    private final ProfileMapper profileMapper;
    private final UserMapper userMapper;
    private final AdminGuard adminGuard;

    @Value("${app.upload.avatar-dir}")
    private String avatarDir;

    @Value("${server.servlet.context-path:/}")
    private String contextPath;

    @Override
    public ProfileDto getSitePublicProfile() {
        ProfileEntity siteOwner = profileMapper.selectSiteOwner();
        if (siteOwner != null) {
            return toDto(siteOwner);
        }
        UserEntity admin = userMapper.selectFirstByRole(UserRole.admin.name());
        if (admin != null) {
            return toDto(getOrCreateProfileForUser(admin));
        }
        throw new BusinessException(ErrorCode.PROFILE_NOT_FOUND, "站点主人资料未配置");
    }

    @Override
    public ProfileDto getProfileByUserId(Long userId) {
        if (userId == null || userId <= 0) {
            throw new BusinessException(ErrorCode.PROFILE_NOT_FOUND, "用户不存在");
        }
        UserEntity user = userMapper.selectById(userId);
        if (user == null) {
            throw new BusinessException(ErrorCode.PROFILE_NOT_FOUND, "用户不存在");
        }
        return toDto(getOrCreateProfileForUser(user));
    }

    @Override
    public ProfileDto getCurrentUserProfile() {
        UserEntity user = requireCurrentUser();
        return toDto(getOrCreateProfileForUser(user));
    }

    @Override
    @Transactional
    public ProfileDto updateCurrentUserProfile(ProfileUpdateRequest request) {
        UserEntity user = requireCurrentUser();
        ProfileEntity entity = getOrCreateProfileForUser(user);
        applyProfilePatch(entity, request);
        profileMapper.update(entity);
        return toDto(entity);
    }

    @Override
    @Transactional
    public AvatarUploadResultDto uploadAvatar(MultipartFile file) throws IOException {
        UserEntity user = requireCurrentUser();
        if (file == null || file.isEmpty()) {
            throw new BusinessException(ErrorCode.TITLE_REQUIRED, "请选择图片文件");
        }

        String contentType = file.getContentType();
        if (contentType == null || !contentType.startsWith("image/")) {
            throw new BusinessException(ErrorCode.TITLE_REQUIRED, "仅支持图片格式");
        }

        Path dir = Paths.get(avatarDir);
        Files.createDirectories(dir);

        String ext = switch (contentType) {
            case "image/png" -> "png";
            case "image/webp" -> "webp";
            case "image/gif" -> "gif";
            default -> "jpg";
        };
        String filename = UUID.randomUUID() + "." + ext;
        Path target = dir.resolve(filename);
        Files.write(target, file.getBytes());

        String base = contextPath.endsWith("/") ? contextPath.substring(0, contextPath.length() - 1) : contextPath;
        String avatarUrl = base + "/uploads/avatars/" + filename;

        ProfileEntity profile = getOrCreateProfileForUser(user);
        profile.setAvatarUrl(avatarUrl);
        profileMapper.update(profile);

        return new AvatarUploadResultDto(avatarUrl);
    }

    @Override
    @Transactional
    public void ensureProfileForUser(UserEntity user) {
        if (user == null || user.getId() == null) {
            return;
        }
        if (profileMapper.selectByUserId(user.getId()) != null) {
            return;
        }
        createDefaultProfile(user);
    }

    @Override
    public boolean isAgentReplyOwnerOnly() {
        ProfileEntity siteOwner = profileMapper.selectSiteOwner();
        if (siteOwner != null) {
            return siteOwner.isAgentReplyOwnerOnly();
        }
        UserEntity admin = userMapper.selectFirstByRole(UserRole.admin.name());
        if (admin == null) {
            return false;
        }
        ProfileEntity profile = profileMapper.selectByUserId(admin.getId());
        return profile != null && profile.isAgentReplyOwnerOnly();
    }

    @Override
    @Transactional
    public void setAgentReplyOwnerOnly(boolean ownerOnlyVisible) {
        adminGuard.requireAdmin();
        UserEntity user = requireCurrentUser();
        ProfileEntity entity = getOrCreateProfileForUser(user);
        entity.setAgentReplyOwnerOnly(ownerOnlyVisible);
        profileMapper.update(entity);
    }

    private UserEntity requireCurrentUser() {
        AuthUserPrincipal principal = adminGuard.requireAuthenticated();
        UserEntity user = userMapper.selectByEmail(principal.getEmail());
        if (user == null) {
            throw new BusinessException(ErrorCode.UNAUTHORIZED);
        }
        return user;
    }

    private ProfileEntity getOrCreateProfileForUser(UserEntity user) {
        ProfileEntity profile = profileMapper.selectByUserId(user.getId());
        if (profile != null) {
            return profile;
        }
        return createDefaultProfile(user);
    }

    private ProfileEntity createDefaultProfile(UserEntity user) {
        ProfileEntity created = new ProfileEntity();
        created.setUserId(user.getId());
        created.setName(defaultDisplayName(user.getEmail()));
        created.setSubtitle("Personal Learning Blog");
        created.setBio("记录前端、工程化与日常学习心得。");
        created.setFocusJson(JsonUtil.toJson(List.of("Vue / TypeScript", "工程化")));
        created.setAvatarUrl("/avatars/default.svg");
        created.setSiteOwner(shouldBeSiteOwner(user));
        profileMapper.insert(created);
        return created;
    }

    private boolean shouldBeSiteOwner(UserEntity user) {
        if (profileMapper.countSiteOwners() > 0) {
            return false;
        }
        return user.getRole() == UserRole.admin;
    }

    private String defaultDisplayName(String email) {
        if (email == null || email.isBlank()) {
            return "新用户";
        }
        int at = email.indexOf('@');
        String local = at > 0 ? email.substring(0, at) : email;
        return local.length() > 32 ? local.substring(0, 32) : local;
    }

    private void applyProfilePatch(ProfileEntity entity, ProfileUpdateRequest request) {
        if (request.getName() != null) {
            String name = request.getName().trim();
            if (name.isEmpty() || name.length() > 32) {
                throw new BusinessException(ErrorCode.TITLE_REQUIRED, "昵称无效");
            }
            entity.setName(name);
        }
        if (request.getSubtitle() != null) {
            entity.setSubtitle(request.getSubtitle().trim().substring(0, Math.min(64, request.getSubtitle().length())));
        }
        if (request.getBio() != null) {
            entity.setBio(request.getBio().length() > 500 ? request.getBio().substring(0, 500) : request.getBio());
        }
        if (request.getFocus() != null) {
            List<String> focus = request.getFocus().stream()
                    .map(String::trim)
                    .filter(s -> !s.isEmpty())
                    .map(s -> s.length() > 20 ? s.substring(0, 20) : s)
                    .limit(10)
                    .toList();
            entity.setFocusJson(JsonUtil.toJson(focus));
        }
        if (request.getAvatarUrl() != null && !request.getAvatarUrl().isBlank()) {
            entity.setAvatarUrl(request.getAvatarUrl().trim());
        }
    }

    private ProfileDto toDto(ProfileEntity entity) {
        ProfileDto dto = new ProfileDto();
        dto.setUserId(entity.getUserId());
        dto.setName(entity.getName());
        dto.setSubtitle(entity.getSubtitle());
        dto.setBio(entity.getBio());
        dto.setFocus(JsonUtil.fromJson(entity.getFocusJson()));
        dto.setAvatarUrl(entity.getAvatarUrl());
        dto.setSiteOwner(entity.isSiteOwner());
        return dto;
    }
}
