package com.personalblog.service;

import com.personalblog.common.PageResult;
import com.personalblog.dto.NoteDto;
import com.personalblog.dto.NoteWriteRequest;

public interface NoteService {

    PageResult<NoteDto> listNotes(
            String topicId,
            String keyword,
            String status,
            String tag,
            String yearMonth,
            int page,
            int pageSize,
            String sort);

    NoteDto getNote(String id);

    NoteDto createNote(NoteWriteRequest request);

    NoteDto updateNote(String id, NoteWriteRequest request);

    void deleteNote(String id);

    /** 切换置顶；全局仅一篇 pinned=true */
    NoteDto pinNote(String id);
}
