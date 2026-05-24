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

    @GetMapping
    public ApiResponse<ProfileDto> getProfile() {
        return ApiResponse.ok(profileService.getProfile());
    }

    /** 公开资料：着陆页与游客浏览使用，无需登录 */
    @GetMapping("/public")
    public ApiResponse<ProfileDto> getPublicProfile() {
        return ApiResponse.ok(profileService.getProfile());
    }

    @PutMapping
    public ApiResponse<ProfileDto> updateProfile(@RequestBody ProfileUpdateRequest request) {
        return ApiResponse.ok(profileService.updateProfile(request));
    }

    @PostMapping("/avatar")
    public ApiResponse<AvatarUploadResultDto> uploadAvatar(@RequestParam("file") MultipartFile file)
            throws IOException {
        return ApiResponse.ok(profileService.uploadAvatar(file));
    }
}
