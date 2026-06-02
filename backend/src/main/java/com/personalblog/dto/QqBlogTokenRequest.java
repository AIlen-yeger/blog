package com.personalblog.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import lombok.Data;

@Data
public class QqBlogTokenRequest {

    /** 主号 QQ（纯数字），对应博客账号邮箱 {qq}@qq.com */
    @NotBlank
    @Pattern(regexp = "^\\d{5,15}$", message = "qq 须为数字 QQ 号")
    private String qq;
}
