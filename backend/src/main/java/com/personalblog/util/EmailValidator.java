package com.personalblog.util;

import com.personalblog.common.BusinessException;
import com.personalblog.common.ErrorCode;

import java.util.regex.Pattern;

public final class EmailValidator {

    private static final Pattern QQ_EMAIL = Pattern.compile("^[^\\s@]+@qq\\.com$", Pattern.CASE_INSENSITIVE);

    private EmailValidator() {
    }

    public static String normalize(String email) {
        if (email == null || !QQ_EMAIL.matcher(email.trim()).matches()) {
            throw new BusinessException(ErrorCode.INVALID_QQ_EMAIL);
        }
        return email.trim().toLowerCase();
    }

    public static void validatePassword(String password) {
        if (password == null || password.length() < 6) {
            throw new BusinessException(ErrorCode.PASSWORD_TOO_SHORT);
        }
    }
}
