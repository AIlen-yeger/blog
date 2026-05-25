package com.personalblog.service.impl;

import com.personalblog.common.BusinessException;
import com.personalblog.common.ErrorCode;
import com.personalblog.service.MailService;
import jakarta.annotation.PostConstruct;
import jakarta.mail.MessagingException;
import jakarta.mail.internet.MimeMessage;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

/** QQ 邮箱 SMTP 发注册验证码。 */
@Service
@RequiredArgsConstructor
@Slf4j
public class QqSmtpMailServiceImpl implements MailService {

    private final JavaMailSender mailSender;

    @Value("${app.mail.enabled:true}")
    private boolean mailEnabled;

    @Value("${app.mail.from}")
    private String from;

    @Value("${app.mail.from-name:}")
    private String fromName;

    @Value("${app.mail.reply-to:}")
    private String replyTo;

    @Value("${app.mail.subject:个人博客注册验证码}")
    private String subject;

    @Value("${app.register.code-ttl-seconds:300}")
    private int codeTtlSeconds;

    @Value("${app.dev.fixed-verification-code:}")
    private String fixedVerificationCode;

    @Value("${spring.mail.username:}")
    private String smtpUsername;

    @Value("${spring.mail.password:}")
    private String smtpPassword;

    @PostConstruct
    void logSmtpConfigStatus() {
        log.info(
                "[smtp-config] provider=smtp, from={}, smtpUser={}, authCode={}, mailEnabled={}, devFixedCode={}",
                from,
                StringUtils.hasText(smtpUsername) ? smtpUsername : "MISSING",
                maskSecret(smtpPassword),
                mailEnabled,
                StringUtils.hasText(fixedVerificationCode) ? "ON" : "OFF"
        );
    }

    @Override
    public void sendRegisterVerificationCode(String toEmail, String code) {
        if (StringUtils.hasText(fixedVerificationCode)) {
            log.info("[dev] 固定验证码模式：{} -> {}，已跳过 SMTP 发信", toEmail, fixedVerificationCode);
            return;
        }
        if (!mailEnabled) {
            log.info("[smtp-skip] 验证码 {} 已生成，目标 {}（未开启真实发信）", code, toEmail);
            return;
        }
        if (!StringUtils.hasText(smtpPassword)) {
            throw new BusinessException(
                    ErrorCode.MAIL_SEND_FAILED,
                    "未配置 QQ 邮箱 SMTP 授权码，请设置环境变量 QQ_SMTP_AUTH_CODE 或 spring.mail.password"
            );
        }

        try {
            MimeMessage message = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");
            helper.setFrom(formatFromAddress());
            helper.setTo(toEmail);
            helper.setSubject(subject + code);
            helper.setText(buildTextBody(code), buildHtmlBody(code));

            String reply = StringUtils.hasText(replyTo) ? replyTo.trim() : from.trim();
            if (StringUtils.hasText(reply)) {
                helper.setReplyTo(reply);
            }

            mailSender.send(message);
            log.info("[smtp] 验证码邮件已发送至 {}（via QQ SMTP）", toEmail);
        } catch (MessagingException ex) {
            log.error("[smtp] 发送失败, to={}, message={}", toEmail, ex.getMessage());
            throw new BusinessException(ErrorCode.MAIL_SEND_FAILED, mapSmtpError(ex));
        }
    }

    private String formatFromAddress() throws MessagingException {
        String email = from != null ? from.trim() : "";
        if (!StringUtils.hasText(email)) {
            email = smtpUsername != null ? smtpUsername.trim() : "";
        }
        if (!StringUtils.hasText(fromName)) {
            return email;
        }
        return fromName.trim() + " <" + email + ">";
    }

    private static String maskSecret(String value) {
        if (!StringUtils.hasText(value)) {
            return "MISSING";
        }
        String v = value.trim();
        if (v.length() <= 4) {
            return "OK";
        }
        return "OK(" + v.substring(0, 2) + "..." + ")";
    }

    private String mapSmtpError(MessagingException ex) {
        String msg = ex.getMessage() != null ? ex.getMessage() : "";
        if (msg.contains("535") || msg.toLowerCase().contains("authentication")) {
            return "QQ 邮箱 SMTP 认证失败，请检查授权码（非 QQ 密码）与 spring.mail.username";
        }
        if (msg.contains("Could not connect")) {
            return "无法连接 smtp.qq.com，请检查网络或端口 465";
        }
        return "验证码邮件发送失败：" + msg;
    }

    private String buildTextBody(String code) {
        int minutes = Math.max(1, codeTtlSeconds / 60);
        return """
                你正在注册个人博客，验证码：%s
                验证码 %d 分钟内有效，请勿泄露。
                如非本人操作请忽略此邮件。
                """.formatted(code, minutes).trim();
    }

    private String buildHtmlBody(String code) {
        int minutes = Math.max(1, codeTtlSeconds / 60);
        return """
                <div style="font-family:sans-serif;line-height:1.6;color:#333;">
                  <p>你好，</p>
                  <p>你正在注册个人博客，验证码为：</p>
                  <p style="font-size:28px;font-weight:bold;letter-spacing:6px;color:#2563eb;">%s</p>
                  <p>验证码 %d 分钟内有效，请勿泄露给他人。</p>
                  <p style="color:#888;font-size:12px;">如非本人操作，请忽略此邮件。</p>
                </div>
                """.formatted(code, minutes);
    }
}
