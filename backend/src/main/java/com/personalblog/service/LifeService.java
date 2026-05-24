package com.personalblog.service;

import com.personalblog.common.PageResult;
import com.personalblog.dto.LifeDto;
import com.personalblog.dto.LifeWriteRequest;

public interface LifeService {

    PageResult<LifeDto> listLife(
            String keyword,
            String status,
            String tag,
            String yearMonth,
            int page,
            int pageSize,
            String sort);

    LifeDto createLife(LifeWriteRequest request);

    LifeDto updateLife(String id, LifeWriteRequest request);

    void deleteLife(String id);

    /** 切换置顶；生活记录全局仅一篇 pinned=true */
    LifeDto pinLife(String id);
}
