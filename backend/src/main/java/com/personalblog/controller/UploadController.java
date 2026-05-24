package com.personalblog.controller;

import com.personalblog.common.ApiResponse;
import com.personalblog.dto.ImageUploadResultDto;
import com.personalblog.service.ContentUploadService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;

@RestController
@RequestMapping("/uploads")
@RequiredArgsConstructor
public class UploadController {

    private final ContentUploadService contentUploadService;

    /** 笔记 / 生活记录正文配图上传（需管理员登录） */
    @PostMapping("/images")
    public ApiResponse<ImageUploadResultDto> uploadContentImage(@RequestParam("file") MultipartFile file)
            throws IOException {
        return ApiResponse.ok(contentUploadService.uploadImage(file));
    }
}
