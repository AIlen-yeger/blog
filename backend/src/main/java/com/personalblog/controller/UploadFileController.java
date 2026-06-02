package com.personalblog.controller;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.CacheControl;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Duration;
import java.util.Locale;
import java.util.regex.Pattern;

/**
 * 本地静态上传文件（头像/正文图）；避免 ResourceHandler 在异常时返回 JSON 500。
 */
@RestController
public class UploadFileController {

    private static final Pattern SAFE_FILENAME =
            Pattern.compile("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\\.[a-z]{3,4}$");

    @Value("${app.upload.avatar-dir}")
    private String avatarDir;

    @Value("${app.upload.content-dir}")
    private String contentDir;

    @GetMapping("/uploads/avatars/{filename}")
    public ResponseEntity<Resource> avatar(@PathVariable String filename) {
        return serveFile(avatarDir, filename);
    }

    @GetMapping("/uploads/content/{filename}")
    public ResponseEntity<Resource> content(@PathVariable String filename) {
        return serveFile(contentDir, filename);
    }

    private ResponseEntity<Resource> serveFile(String baseDir, String filename) {
        if (filename == null || !SAFE_FILENAME.matcher(filename.toLowerCase(Locale.ROOT)).matches()) {
            return ResponseEntity.badRequest().build();
        }
        Path base = Paths.get(baseDir).toAbsolutePath().normalize();
        Path file = base.resolve(filename).normalize();
        if (!file.startsWith(base) || !Files.isRegularFile(file)) {
            return ResponseEntity.notFound().build();
        }
        FileSystemResource resource = new FileSystemResource(file);
        MediaType mediaType = probeMediaType(filename);
        return ResponseEntity.ok()
                .cacheControl(CacheControl.maxAge(Duration.ofDays(7)).cachePublic())
                .contentType(mediaType)
                .body(resource);
    }

    private static MediaType probeMediaType(String filename) {
        String ext = filename.substring(filename.lastIndexOf('.') + 1).toLowerCase(Locale.ROOT);
        return switch (ext) {
            case "png" -> MediaType.IMAGE_PNG;
            case "gif" -> MediaType.IMAGE_GIF;
            case "webp" -> MediaType.parseMediaType("image/webp");
            default -> MediaType.IMAGE_JPEG;
        };
    }
}
