package com.personalblog.service.impl;

import com.personalblog.dto.QqBlogTokenDto;
import com.personalblog.entity.UserEntity;
import com.personalblog.mapper.UserMapper;
import com.personalblog.security.JwtService;
import com.personalblog.service.AgentQqBridgeService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class AgentQqBridgeServiceImpl implements AgentQqBridgeService {

    private final UserMapper userMapper;
    private final JwtService jwtService;

    @Override
    public QqBlogTokenDto issueTokenForQq(String qqDigits) {
        String digits = (qqDigits == null ? "" : qqDigits).trim().replaceAll("\\D", "");
        if (digits.isEmpty()) {
            return QqBlogTokenDto.builder().found(false).build();
        }
        String email = digits.toLowerCase() + "@qq.com";
        UserEntity user = userMapper.selectByEmail(email);
        if (user == null || user.getId() == null) {
            return QqBlogTokenDto.builder()
                    .found(false)
                    .email(email)
                    .build();
        }
        String token = jwtService.generateToken(user.getEmail(), user.getRole(), user.getId());
        return QqBlogTokenDto.builder()
                .found(true)
                .userId(user.getId())
                .email(user.getEmail())
                .role(user.getRole())
                .accessToken(token)
                .expiresIn(jwtService.getExpirationSeconds())
                .build();
    }
}
