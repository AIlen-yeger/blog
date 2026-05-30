package com.personalblog.entity;

import lombok.Getter;
import lombok.Setter;

import java.time.LocalDate;

@Getter
@Setter
public class UserCheckInEntity {

    private Long id;
    private Long userId;
    private LocalDate checkInDate;
}
