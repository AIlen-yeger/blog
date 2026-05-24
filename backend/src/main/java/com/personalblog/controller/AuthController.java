package com.personalblog.controller;

import com.personalblog.common.ApiResponse;
import com.personalblog.dto.*;
import com.personalblog.service.AuthService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/auth")
@RequiredArgsConstructor
@Slf4j
public class AuthController {

    private final AuthService authService;

    @PostMapping("/login")
    public ApiResponse<LoginResultDto> login(@Valid @RequestBody LoginRequest request) {
        return ApiResponse.ok(authService.login(request));
    }

    @PostMapping("/register/send-code")
    public ApiResponse<SendCodeResultDto> sendCode(@Valid @RequestBody RegisterCodeRequest request) {
        return ApiResponse.ok(authService.sendRegisterCode(request));
    }

    @PostMapping("/register/verify")
    public ApiResponse<LoginResultDto> verify(@Valid @RequestBody RegisterVerifyRequest request) {
        return ApiResponse.ok(authService.verifyRegister(request));
    }

    @PostMapping("/register/resend-code")
    public ApiResponse<SendCodeResultDto> resend(@Valid @RequestBody ResendCodeRequest request) {
        return ApiResponse.ok(authService.resendCode(request));
    }
}
