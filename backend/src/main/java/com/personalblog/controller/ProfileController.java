package com.personalblog.controller;

import com.personalblog.common.ApiResponse;
import com.personalblog.dto.AvatarUploadResultDto;
import com.personalblog.dto.ProfileDto;
import com.personalblog.dto.ProfileUpdateRequest;
import com.personalblog.service.ProfileService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;

@RestController
@RequestMapping("/profile")
@RequiredArgsConstructor
public class ProfileController {

    private final ProfileService profileService;

    /** 当前登录用户自己的资料（需登录） */
    @GetMapping
    public ApiResponse<ProfileDto> getProfile() {
        return ApiResponse.ok(profileService.getCurrentUserProfile());
    }

    /** 站点主人公开资料：着陆页与游客浏览 */
    @GetMapping("/public")
    public ApiResponse<ProfileDto> getPublicProfile() {
        return ApiResponse.ok(profileService.getSitePublicProfile());
    }

    /** 指定用户公开资料（后续多用户主页扩展，只读） */
    @GetMapping("/users/{userId}")
    public ApiResponse<ProfileDto> getUserProfile(@PathVariable Long userId) {
        return ApiResponse.ok(profileService.getProfileByUserId(userId));
    }

    @PutMapping
    public ApiResponse<ProfileDto> updateProfile(@RequestBody ProfileUpdateRequest request) {
        return ApiResponse.ok(profileService.updateCurrentUserProfile(request));
    }

    @PostMapping("/avatar")
    public ApiResponse<AvatarUploadResultDto> uploadAvatar(@RequestParam("file") MultipartFile file)
            throws IOException {
        return ApiResponse.ok(profileService.uploadAvatar(file));
    }
}
