package com.personalblog.service;

import com.personalblog.dto.*;

public interface AuthService {

    LoginResultDto login(LoginRequest request);

    SendCodeResultDto sendRegisterCode(RegisterCodeRequest request);

    LoginResultDto verifyRegister(RegisterVerifyRequest request);

    SendCodeResultDto resendCode(ResendCodeRequest request);
}
