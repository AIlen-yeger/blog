package com.personalblog.entity;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class UserEntity {

    private Long id;
    private String email;
    private String passwordHash;
    private UserRole role = UserRole.user;
}
