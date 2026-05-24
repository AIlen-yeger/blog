package com.personalblog.dto;

import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class SendCodeResultDto {
    private String email;
    private int expiresIn;
}
