package com.personalblog.common;

import lombok.Getter;
import lombok.RequiredArgsConstructor;

@Getter
@RequiredArgsConstructor
public enum ErrorCode {
    OK(0, "ok"),
    INVALID_QQ_EMAIL(40001, "请使用 QQ 邮箱（@qq.com）"),
    PASSWORD_TOO_SHORT(40002, "密码至少 6 位"),
    WRONG_PASSWORD(40003, "密码错误"),
    INVALID_VERIFICATION_CODE(40004, "验证码错误"),
    TITLE_REQUIRED(40005, "标题不能为空"),
    TOPIC_NOT_FOUND(40006, "专题不存在"),
    UNAUTHORIZED(40101, "未登录或登录已过期"),
    FORBIDDEN(40301, "无权限执行此操作"),
    NOTE_NOT_FOUND(40401, "笔记不存在"),
    LIFE_NOT_FOUND(40402, "生活记录不存在"),
    PROFILE_NOT_FOUND(40404, "资料不存在"),
    /** 登录时邮箱未注册，前端据此进入验证码注册页 */
    ACCOUNT_NOT_REGISTERED(40403, "该邮箱未注册，请完成验证码注册"),
    EMAIL_ALREADY_REGISTERED(40901, "该邮箱已注册"),
    CODE_SEND_TOO_FREQUENT(42901, "验证码发送过于频繁，请稍后再试"),
    CODE_DAILY_LIMIT(42902, "今日验证码发送次数已达上限，请明日再试"),
    MAIL_SEND_FAILED(50001, "验证码邮件发送失败，请稍后重试"),
    INTERNAL_ERROR(50000, "服务器内部错误"),
    NOT_SUPPORTED_FOR_NO(500001,"暂不支持开发者以外的用户注册哦！");

    private final int code;
    private final String message;
}
