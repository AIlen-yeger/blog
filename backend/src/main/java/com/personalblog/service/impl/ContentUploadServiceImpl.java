package com.personalblog.service.impl;

import com.personalblog.common.BusinessException;
import com.personalblog.common.ErrorCode;
import com.personalblog.dto.ImageUploadResultDto;
import com.personalblog.security.AdminGuard;
import com.personalblog.service.ContentUploadService;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class ContentUploadServiceImpl implements ContentUploadService {

    private final AdminGuard adminGuard;

    @Value("${app.upload.content-dir}")
    private String contentDir;

    @Value("${server.servlet.context-path:/}")
    private String contextPath;

    @Override
    public ImageUploadResultDto uploadImage(MultipartFile file) throws IOException {
        adminGuard.requireAdmin();
        if (file == null || file.isEmpty()) {
            throw new BusinessException(ErrorCode.TITLE_REQUIRED, "请选择图片文件");
        }

        String contentType = file.getContentType();
        if (contentType == null || !contentType.startsWith("image/")) {
            throw new BusinessException(ErrorCode.TITLE_REQUIRED, "仅支持图片格式");
        }

        Path dir = Paths.get(contentDir);
        Files.createDirectories(dir);

        String ext = switch (contentType) {
            case "image/png" -> "png";
            case "image/webp" -> "webp";
            case "image/gif" -> "gif";
            default -> "jpg";
        };
        String filename = UUID.randomUUID() + "." + ext;
        Files.write(dir.resolve(filename), file.getBytes());

        String base = contextPath.endsWith("/") ? contextPath.substring(0, contextPath.length() - 1) : contextPath;
        String url = base + "/uploads/content/" + filename;
        return new ImageUploadResultDto(url);
    }
}
