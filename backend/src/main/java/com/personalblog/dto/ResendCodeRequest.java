package com.personalblog.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class ResendCodeRequest {
    @NotBlank
    private String email;
}
