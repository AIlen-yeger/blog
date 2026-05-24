package com.personalblog.service;

import com.personalblog.dto.SearchResultDto;

public interface ContentSearchService {

    SearchResultDto search(String keyword, int limit);
}
