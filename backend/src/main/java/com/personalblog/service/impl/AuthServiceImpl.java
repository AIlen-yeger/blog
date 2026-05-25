package com.personalblog.service.impl;

import com.personalblog.cache.RegisterCodeCache;
import com.personalblog.cache.RegisterPendingData;
import com.personalblog.common.BusinessException;
import com.personalblog.common.ErrorCode;
import com.personalblog.dto.*;
import com.personalblog.entity.UserEntity;
import com.personalblog.entity.UserRole;
import com.personalblog.mapper.UserMapper;
import com.personalblog.security.JwtService;
import com.personalblog.service.AuthService;
import com.personalblog.service.MailService;
import com.personalblog.util.EmailValidator;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Random;
import java.util.prefs.BackingStoreException;

@Service
@RequiredArgsConstructor
@Slf4j
public class AuthServiceImpl implements AuthService {

    private final UserMapper userMapper;
    private final RegisterCodeCache registerCodeCache;
    private final MailService mailService;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;

    @Value("${developer.email:}")
    private String developerEmail;

    @Value("${app.dev.fixed-verification-code:}")
    private String fixedVerificationCode;

    private final Random random = new Random();

    @Override
    public LoginResultDto login(LoginRequest request) {
        String email = EmailValidator.normalize(request.getEmail());
        EmailValidator.validatePassword(request.getPassword());

        UserEntity user = userMapper.selectByEmail(email);
        if (user == null) {
            throw new BusinessException(ErrorCode.ACCOUNT_NOT_REGISTERED);
        }
        if (!passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            throw new BusinessException(ErrorCode.WRONG_PASSWORD);
        }
        return buildLoginResult(user);
    }

    @Override
    public SendCodeResultDto sendRegisterCode(RegisterCodeRequest request) {
        String email = EmailValidator.normalize(request.getEmail());

        if (!email.equals(developerEmail)) throw new BusinessException(ErrorCode.NOT_SUPPORTED_FOR_NO);


        EmailValidator.validatePassword(request.getPassword());

        if (userMapper.countByEmail(email) > 0) {
            throw new BusinessException(ErrorCode.EMAIL_ALREADY_REGISTERED);
        }

        return issueVerificationCode(email, passwordEncoder.encode(request.getPassword()));
    }

    @Override
    @Transactional
    public LoginResultDto verifyRegister(RegisterVerifyRequest request) {
        String email = EmailValidator.normalize(request.getEmail());
        if (!email.equals(developerEmail)) throw new BusinessException(ErrorCode.NOT_SUPPORTED_FOR_NO);
        EmailValidator.validatePassword(request.getPassword());

        RegisterPendingData pending = registerCodeCache.getPending(email);
        if (pending == null) {
            throw new BusinessException(ErrorCode.INVALID_VERIFICATION_CODE);
        }

        if (!passwordEncoder.matches(request.getPassword(), pending.getPasswordHash())) {
            throw new BusinessException(ErrorCode.INVALID_VERIFICATION_CODE);
        }

        String inputCode = request.getCode() != null ? request.getCode().trim() : "";
        boolean valid = pending.getCode().equals(inputCode)
                || (!fixedVerificationCode.isBlank() && fixedVerificationCode.equals(inputCode));
        if (!valid) {
            throw new BusinessException(ErrorCode.INVALID_VERIFICATION_CODE);
        }

        UserEntity user = userMapper.selectByEmail(email);
        if (user == null) {
            user = new UserEntity();
            user.setEmail(email);
            user.setPasswordHash(pending.getPasswordHash());
            user.setRole(UserRole.user);
            userMapper.insert(user);
        }

        registerCodeCache.clearPending(email);
        return buildLoginResult(user);
    }

    @Override
    public SendCodeResultDto resendCode(ResendCodeRequest request) {
        String email = EmailValidator.normalize(request.getEmail());

        if (userMapper.countByEmail(email) > 0) {
            throw new BusinessException(ErrorCode.EMAIL_ALREADY_REGISTERED);
        }

        RegisterPendingData pending = registerCodeCache.getPending(email);
        if (pending == null) {
            throw new BusinessException(ErrorCode.INVALID_VERIFICATION_CODE);
        }

        return issueVerificationCode(email, pending.getPasswordHash());
    }

    /**
     * 限流 → 生成验证码 → 写入 Redis → 发信（默认 QQ SMTP）。
     */
    private SendCodeResultDto issueVerificationCode(String email, String passwordHash) {
        if (registerCodeCache.isInCooldown(email)) {
            throw new BusinessException(ErrorCode.CODE_SEND_TOO_FREQUENT);
        }

        registerCodeCache.checkAndRecordDailySend(email);

        String code = generateCode();
        registerCodeCache.savePending(email, code, passwordHash);
        try {
            mailService.sendRegisterVerificationCode(email, code);
        } catch (BusinessException ex) {
            registerCodeCache.clearPending(email);
            throw ex;
        }

        return new SendCodeResultDto(email, registerCodeCache.getCodeTtlSeconds());
    }

    private String generateCode() {
        if (!fixedVerificationCode.isBlank()) {
            return fixedVerificationCode;
        }
        return String.format("%06d", random.nextInt(1_000_000));
    }

    private LoginResultDto buildLoginResult(UserEntity user) {
        String token = jwtService.generateToken(user.getEmail(), user.getRole());
        LoginResultDto.UserInfoDto userInfo = new LoginResultDto.UserInfoDto(user.getEmail(), user.getRole());
        return new LoginResultDto(token, jwtService.getExpirationSeconds(), userInfo);
    }
}
