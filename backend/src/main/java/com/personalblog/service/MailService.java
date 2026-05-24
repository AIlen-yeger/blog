package com.personalblog.service;

/**
 * 邮件发送（QQ 邮箱 SMTP）。
 */
public interface MailService {

    /**
     * 向注册邮箱发送 6 位数字验证码。
     */
    void sendRegisterVerificationCode(String toEmail, String code);
}
