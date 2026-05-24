package com.personalblog.dto;

import com.personalblog.entity.UserRole;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class LoginResultDto {
    private String token;
    private long expiresIn;
    private UserInfoDto user;

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UserInfoDto {
        private String email;
        private UserRole role;
    }
}
