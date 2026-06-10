package com.personalblog.service;

import com.personalblog.dto.DocumentUploadResultDto;
import com.personalblog.dto.ImageUploadResultDto;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;

public interface ContentUploadService {
    ImageUploadResultDto uploadImage(MultipartFile file) throws IOException;

    DocumentUploadResultDto uploadDocument(MultipartFile file) throws IOException;
}
