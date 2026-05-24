package com.personalblog.service.impl;

import com.personalblog.common.BusinessException;
import com.personalblog.common.ErrorCode;
import com.personalblog.config.TencentSesProperties;
import com.personalblog.service.MailService;
import com.tencentcloudapi.common.Credential;
import com.tencentcloudapi.common.exception.TencentCloudSDKException;
import com.tencentcloudapi.common.profile.ClientProfile;
import com.tencentcloudapi.common.profile.HttpProfile;
import com.tencentcloudapi.ses.v20201002.SesClient;
import com.tencentcloudapi.ses.v20201002.models.SendEmailRequest;
import com.tencentcloudapi.ses.v20201002.models.Simple;
import com.tencentcloudapi.ses.v20201002.models.Template;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.nio.charset.StandardCharsets;
import java.util.Base64;

/**
 * 腾讯云 SES 发信（与控制台验证过的 QQ 邮箱发件地址配合使用）。
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class TencentSesMailServiceImpl implements MailService {

    private static final long TRIGGER_TYPE_VERIFICATION = 1L;

    private final TencentSesProperties sesProperties;

    @Value("${app.mail.enabled:true}")
    private boolean mailEnabled;

    @Value("${app.mail.from}")
    private String from;

    /** 发件人展示名，与邮箱之间一个空格，格式：昵称 <email@qq.com> */
    @Value("${app.mail.from-name:}")
    private String fromName;

    @Value("${app.mail.reply-to:}")
    private String replyTo;

    @Value("${app.mail.subject:个人博客注册验证码}")
    private String subject;

    /** 大于 0 时使用模板发送，模板变量名需包含 code */
    @Value("${app.mail.template-id:0}")
    private long templateId;

    @Value("${app.register.code-ttl-seconds:300}")
    private int codeTtlSeconds;

    /** 配置后本地可无 SES 密钥，验证码固定为该值 */
    @Value("${app.dev.fixed-verification-code:}")
    private String fixedVerificationCode;

    @Override
    public void sendRegisterVerificationCode(String toEmail, String code) {
        if (StringUtils.hasText(fixedVerificationCode)) {
            log.info("[dev] 固定验证码模式：{} -> {}，已跳过 SES（模板审核通过后可关闭 app.dev.fixed-verification-code）",
                    toEmail, fixedVerificationCode);
            return;
        }
        if (!mailEnabled) {
            log.info("[ses-skip] 验证码 {} 已生成，目标 {}（未开启真实发信）", code, toEmail);
            return;
        }
        if (!hasSesCredentials()) {
            throw new BusinessException(ErrorCode.MAIL_SEND_FAILED, "未配置腾讯云密钥");
        }

        try {
            SesClient client = buildClient();
            SendEmailRequest req = new SendEmailRequest();
            req.setFromEmailAddress(formatFromAddress());
            req.setSubject(subject + code);
            req.setDestination(new String[]{toEmail});
            req.setTriggerType(TRIGGER_TYPE_VERIFICATION);
            req.setUnsubscribe("0");

            String reply = StringUtils.hasText(replyTo) ? replyTo : from;
            if (StringUtils.hasText(reply)) {
                req.setReplyToAddresses(reply);
            }

            if (templateId > 0) {
                Template template = new Template();
                template.setTemplateID(templateId);
                template.setTemplateData("{\"code\":\"" + escapeJson(code) + "\"}");
                req.setTemplate(template);
            } else {
                Simple simple = new Simple();
                simple.setHtml(Base64.getEncoder().encodeToString(
                        buildHtmlBody(code).getBytes(StandardCharsets.UTF_8)));
                simple.setText(Base64.getEncoder().encodeToString(
                        buildTextBody(code).getBytes(StandardCharsets.UTF_8)));
                req.setSimple(simple);
            }

            client.SendEmail(req);
            log.info("[ses] 验证码邮件已发送至 {}（region={}, templateId={}）",
                    toEmail, sesProperties.getRegion(), templateId);
        } catch (TencentCloudSDKException ex) {
            log.error("[ses] 发送失败, to={}, code={}, requestId={}, message={}",
                    toEmail, ex.getErrorCode(), ex.getRequestId(), ex.getMessage());
            throw new BusinessException(ErrorCode.MAIL_SEND_FAILED, mapSesError(ex));
        }
    }

    private boolean hasSesCredentials() {
        return StringUtils.hasText(resolveSecretId()) && StringUtils.hasText(resolveSecretKey());
    }

    private SesClient buildClient() {
        Credential cred = new Credential(resolveSecretId(), resolveSecretKey());
        HttpProfile httpProfile = new HttpProfile();
        httpProfile.setEndpoint(resolveEndpoint());

        ClientProfile clientProfile = new ClientProfile();
        clientProfile.setHttpProfile(httpProfile);

        return new SesClient(cred, sesProperties.getRegion(), clientProfile);
    }


    private String resolveSecretId() {
        return firstNonBlank(
                System.getenv("TENCENTCLOUD_SECRET_ID"),
                System.getenv("SecretId"),
                sesProperties.getSecretId());
    }

    private String resolveSecretKey() {
        return firstNonBlank(
                System.getenv("TENCENTCLOUD_SECRET_KEY"),
                System.getenv("SecretKey"),
                sesProperties.getSecretKey());
    }

    private static String firstNonBlank(String... candidates) {
        for (String value : candidates) {
            if (StringUtils.hasText(value)) {
                return value.trim();
            }
        }
        return "";
    }

    private String resolveEndpoint() {
        String endpoint = sesProperties.getEndpoint();
        String region = sesProperties.getRegion();
        if (!StringUtils.hasText(endpoint) || "ses.tencentcloudapi.com".equals(endpoint)) {
            return "ses." + region + ".tencentcloudapi.com";
        }
        return endpoint;
    }

    private String formatFromAddress() {
        String email = from != null ? from.trim() : "";
        if (!StringUtils.hasText(fromName)) {
            return email;
        }
        return fromName.trim() + " <" + email + ">";
    }

    private static String escapeJson(String value) {
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    private String mapSesError(TencentCloudSDKException ex) {
        String code = ex.getErrorCode() != null ? ex.getErrorCode() : "";
        return switch (code) {
            case "FailedOperation.NotAuthenticatedSender" ->
                    "发件邮箱未在腾讯云 SES（广州）完成验证，请先在控制台认证 " + from;
            case "FailedOperation.WithOutPermission" ->
                    "当前 SES 账号仅支持模板发信，请在控制台创建验证码模板并配置 app.mail.template-id";
            case "FailedOperation.InvalidTemplateID" ->
                    "邮件模板 ID 无效或未审核通过，请检查 app.mail.template-id";
            case "FailedOperation.IncorrectSender" ->
                    "发件人格式不正确，请配置 app.mail.from 与 app.mail.from-name，且与控制台一致";
            case "FailedOperation.InsufficientBalance", "FailedOperation.InsufficientQuota" ->
                    "SES 余额或发信额度不足，请在腾讯云邮件推送控制台充值或购买套餐";
            case "FailedOperation.ExceedSendLimit", "FailedOperation.FrequencyLimit" ->
                    "今日发信次数或频率超限，请稍后再试";
            case "FailedOperation.SendEmailErr" -> templateId <= 0
                    ? "SES 发信失败：多数账号需使用已审核模板（配置 template-id），并确认发件地址已在广州地域验证"
                    : "SES 发信失败，请确认发件地址、模板与地域 ap-guangzhou 一致：" + ex.getMessage();
            default -> "验证码邮件发送失败：" + (ex.getMessage() != null ? ex.getMessage() : code);
        };
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
                  <p>你正在注册Run的个人博客，验证码为：</p>
                  <p style="font-size:28px;font-weight:bold;letter-spacing:6px;color:#2563eb;">%s</p>
                  <p>验证码 %d 分钟内有效，请勿泄露给他人。</p>
                  <p style="color:#888;font-size:12px;">如非本人操作，请忽略此邮件。</p>
                </div>
                """.formatted(code, minutes);
    }
}
