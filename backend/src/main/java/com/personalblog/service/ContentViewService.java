package com.personalblog.service;

import com.personalblog.dto.ViewRecordResultDto;
import jakarta.servlet.http.HttpServletRequest;

public interface ContentViewService {

    ViewRecordResultDto recordNoteView(String noteId, HttpServletRequest request);

    ViewRecordResultDto recordLifeView(String lifeId, HttpServletRequest request);
}
