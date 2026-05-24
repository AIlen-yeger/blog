package com.personalblog.dto;

import lombok.Data;

import java.util.List;

@Data
public class ProfileDto {
    private String name;
    private String subtitle;
    private String bio;
    private List<String> focus;
    private String avatarUrl;
}
