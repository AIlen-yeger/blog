package com.personalblog.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class RegisterVerifyRequest {
    @NotBlank
    private String email;
    @NotBlank
    private String password;
    @NotBlank
    private String code;
}
