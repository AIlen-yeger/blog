package com.personalblog.service;

import com.personalblog.dto.QqBlogTokenDto;

public interface AgentQqBridgeService {

    /**
     * 若博客存在邮箱为 {qq}@qq.com 的用户，签发与 Web 登录相同的 JWT。
     */
    QqBlogTokenDto issueTokenForQq(String qqDigits);
}
