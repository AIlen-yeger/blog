package com.personalblog.dto;

import com.personalblog.entity.UserRole;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class QqBlogTokenDto {
    private boolean found;
    private Long userId;
    private String email;
    private UserRole role;
    private String accessToken;
    private long expiresIn;
}
