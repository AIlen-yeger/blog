package com.personalblog.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class DocumentUploadResultDto {

    private String url;
    private String filename;
    private String mime;
    private long size;
}
