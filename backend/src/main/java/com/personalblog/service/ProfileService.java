package com.personalblog.service;

import com.personalblog.dto.AvatarUploadResultDto;
import com.personalblog.dto.ProfileDto;
import com.personalblog.dto.ProfileUpdateRequest;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;

public interface ProfileService {

    ProfileDto getProfile();

    ProfileDto updateProfile(ProfileUpdateRequest request);

    AvatarUploadResultDto uploadAvatar(MultipartFile file) throws IOException;
}
