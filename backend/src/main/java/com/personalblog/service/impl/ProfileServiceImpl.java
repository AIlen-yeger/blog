package com.personalblog.service.impl;

import com.personalblog.common.BusinessException;
import com.personalblog.common.ErrorCode;
import com.personalblog.dto.AvatarUploadResultDto;
import com.personalblog.dto.ProfileDto;
import com.personalblog.dto.ProfileUpdateRequest;
import com.personalblog.entity.ProfileEntity;
import com.personalblog.mapper.ProfileMapper;
import com.personalblog.security.AdminGuard;
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
    private final AdminGuard adminGuard;

    @Value("${app.upload.avatar-dir}")
    private String avatarDir;

    @Value("${server.servlet.context-path:/}")
    private String contextPath;

    @Override
    public ProfileDto getProfile() {
        return toDto(getOrCreateProfile());
    }

    @Override
    @Transactional
    public ProfileDto updateProfile(ProfileUpdateRequest request) {
        adminGuard.requireAdmin();
        ProfileEntity entity = getOrCreateProfile();

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

        profileMapper.update(entity);
        return toDto(entity);
    }

    @Override
    @Transactional
    public AvatarUploadResultDto uploadAvatar(MultipartFile file) throws IOException {
        adminGuard.requireAdmin();
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

        ProfileEntity profile = getOrCreateProfile();
        profile.setAvatarUrl(avatarUrl);
        profileMapper.update(profile);

        return new AvatarUploadResultDto(avatarUrl);
    }

    private ProfileEntity getOrCreateProfile() {
        ProfileEntity profile = profileMapper.selectById(1L);
        if (profile != null) {
            return profile;
        }
        ProfileEntity created = new ProfileEntity();
        created.setId(1L);
        created.setName("奥利奥");
        created.setSubtitle("Personal Learning Blog");
        created.setBio("记录前端、工程化与日常学习心得。");
        created.setFocusJson(JsonUtil.toJson(List.of("Vue / TypeScript", "工程化")));
        created.setAvatarUrl("/avatars/default.svg");
        profileMapper.insert(created);
        return created;
    }

    private ProfileDto toDto(ProfileEntity entity) {
        ProfileDto dto = new ProfileDto();
        dto.setName(entity.getName());
        dto.setSubtitle(entity.getSubtitle());
        dto.setBio(entity.getBio());
        dto.setFocus(JsonUtil.fromJson(entity.getFocusJson()));
        dto.setAvatarUrl(entity.getAvatarUrl());
        return dto;
    }
}
