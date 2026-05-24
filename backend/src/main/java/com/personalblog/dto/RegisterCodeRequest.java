package com.personalblog.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class RegisterCodeRequest {
    @NotBlank
    private String email;
    @NotBlank
    private String password;
}
