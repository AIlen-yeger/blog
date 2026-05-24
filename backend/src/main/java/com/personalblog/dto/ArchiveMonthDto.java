package com.personalblog.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class ArchiveMonthDto {
    /** YYYY-MM */
    private String month;
    private long count;
}
