package com.personalblog.service.impl;

import com.personalblog.common.BusinessException;
import com.personalblog.common.ErrorCode;
import com.personalblog.dto.DocumentUploadResultDto;
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

    @Value("${app.upload.note-images-dir}")
    private String noteImagesDir;

    @Value("${app.upload.document-dir}")
    private String documentDir;

    @Value("${server.servlet.context-path:/}")
    private String contextPath;

    private static final long MAX_DOCUMENT_BYTES = 10L * 1024 * 1024;

    @Override
    public ImageUploadResultDto uploadImage(MultipartFile file) throws IOException {
        return storeImage(file, contentDir, "/uploads/content/");
    }

    @Override
    public ImageUploadResultDto uploadNoteImage(MultipartFile file) throws IOException {
        return storeImage(file, noteImagesDir, "/uploads/note-images/");
    }

    private ImageUploadResultDto storeImage(MultipartFile file, String dirPath, String urlPrefix) throws IOException {
        adminGuard.requireAdmin();
        if (file == null || file.isEmpty()) {
            throw new BusinessException(ErrorCode.TITLE_REQUIRED, "请选择图片文件");
        }

        String contentType = file.getContentType();
        if (contentType == null || !contentType.startsWith("image/")) {
            throw new BusinessException(ErrorCode.TITLE_REQUIRED, "仅支持图片格式");
        }

        Path dir = Paths.get(dirPath);
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
        String url = base + urlPrefix + filename;
        return new ImageUploadResultDto(url);
    }

    @Override
    public DocumentUploadResultDto uploadDocument(MultipartFile file) throws IOException {
        adminGuard.requireAdmin();
        if (file == null || file.isEmpty()) {
            throw new BusinessException(ErrorCode.TITLE_REQUIRED, "请选择文档文件");
        }
        if (file.getSize() > MAX_DOCUMENT_BYTES) {
            throw new BusinessException(ErrorCode.TITLE_REQUIRED, "文档不能超过 10MB");
        }

        String original = file.getOriginalFilename() != null ? file.getOriginalFilename() : "document";
        String ext = extensionOf(original, file.getContentType());
        if (ext == null) {
            throw new BusinessException(ErrorCode.TITLE_REQUIRED, "仅支持 pdf、md、txt、doc、docx");
        }

        Path dir = Paths.get(documentDir);
        Files.createDirectories(dir);

        String filename = UUID.randomUUID() + "." + ext;
        Files.write(dir.resolve(filename), file.getBytes());

        String base = contextPath.endsWith("/") ? contextPath.substring(0, contextPath.length() - 1) : contextPath;
        String url = base + "/uploads/documents/" + filename;
        String mime = file.getContentType() != null ? file.getContentType() : "application/octet-stream";
        return new DocumentUploadResultDto(url, original, mime, file.getSize());
    }

    private static String extensionOf(String filename, String contentType) {
        String lower = filename.toLowerCase();
        if (lower.endsWith(".pdf")) {
            return "pdf";
        }
        if (lower.endsWith(".md") || lower.endsWith(".markdown")) {
            return "md";
        }
        if (lower.endsWith(".txt")) {
            return "txt";
        }
        if (lower.endsWith(".docx")) {
            return "docx";
        }
        if (lower.endsWith(".doc")) {
            return "doc";
        }
        if (contentType != null) {
            return switch (contentType) {
                case "application/pdf" -> "pdf";
                case "text/markdown", "text/plain" -> contentType.contains("markdown") ? "md" : "txt";
                case "application/vnd.openxmlformats-officedocument.wordprocessingml.document" -> "docx";
                case "application/msword" -> "doc";
                default -> null;
            };
        }
        return null;
    }
}
