package com.personalblog.controller;

import com.personalblog.common.ApiResponse;
import com.personalblog.common.PageResult;
import com.personalblog.dto.NoteDto;
import com.personalblog.dto.NoteWriteRequest;
import com.personalblog.dto.ViewRecordResultDto;
import com.personalblog.service.ContentViewService;
import com.personalblog.service.NoteService;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/notes")
@RequiredArgsConstructor
public class NoteController {

    private final NoteService noteService;
    private final ContentViewService contentViewService;

    @GetMapping
    public ApiResponse<PageResult<NoteDto>> listNotes(
            @RequestParam(required = false) String topicId,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String tag,
            @RequestParam(required = false) String yearMonth,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int pageSize,
            @RequestParam(defaultValue = "date_desc") String sort) {
        return ApiResponse.ok(
                noteService.listNotes(topicId, keyword, status, tag, yearMonth, page, pageSize, sort));
    }

    @GetMapping("/{id}")
    public ApiResponse<NoteDto> getNote(@PathVariable String id) {
        return ApiResponse.ok(noteService.getNote(id));
    }

    @PostMapping("/{id}/views")
    public ApiResponse<ViewRecordResultDto> recordView(@PathVariable String id, HttpServletRequest request) {
        return ApiResponse.ok(contentViewService.recordNoteView(id, request));
    }

    @PostMapping("/{id}/pin")
    public ApiResponse<NoteDto> pinNote(@PathVariable String id) {
        return ApiResponse.ok(noteService.pinNote(id));
    }

    @PostMapping
    public ResponseEntity<ApiResponse<NoteDto>> createNote(@RequestBody NoteWriteRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.ok(noteService.createNote(request)));
    }

    @PutMapping("/{id}")
    public ApiResponse<NoteDto> updateNote(@PathVariable String id, @RequestBody NoteWriteRequest request) {
        return ApiResponse.ok(noteService.updateNote(id, request));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteNote(@PathVariable String id) {
        noteService.deleteNote(id);
        return ResponseEntity.noContent().build();
    }
}
