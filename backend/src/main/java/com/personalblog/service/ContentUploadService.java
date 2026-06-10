package com.personalblog.service;

import com.personalblog.dto.DocumentUploadResultDto;
import com.personalblog.dto.ImageUploadResultDto;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;

public interface ContentUploadService {
    ImageUploadResultDto uploadImage(MultipartFile file) throws IOException;

    /** Markdown 正文内嵌图（与头像、编辑器附图目录分离） */
    ImageUploadResultDto uploadNoteImage(MultipartFile file) throws IOException;

    DocumentUploadResultDto uploadDocument(MultipartFile file) throws IOException;
}
