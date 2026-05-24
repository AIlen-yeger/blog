package com.personalblog.dto;

import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class ViewRecordResultDto {
    /** 当前总浏览量（去重后） */
    private int viewCount;
    /** 本次是否新计入一条浏览 */
    private boolean recorded;
}
