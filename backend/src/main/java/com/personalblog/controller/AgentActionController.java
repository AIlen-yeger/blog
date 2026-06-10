package com.personalblog.controller;

import com.personalblog.common.ApiResponse;
import com.personalblog.dto.NoteDto;
import com.personalblog.dto.NoteWriteRequest;
import com.personalblog.dto.PublishNoteActionRequest;
import com.personalblog.dto.UpdateNoteActionRequest;
import com.personalblog.service.NoteService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/agent/actions")
@RequiredArgsConstructor
public class AgentActionController {

    private final NoteService noteService;

    @PostMapping("/publish-note")
    public ResponseEntity<ApiResponse<NoteDto>> publishNote(
            @Valid @RequestBody PublishNoteActionRequest request) {
        NoteWriteRequest body = new NoteWriteRequest();
        body.setTitle(request.getTitle().trim());
        body.setContent(request.getContent().trim());
        body.setTopicTitle(
                request.getTopicTitle() != null && !request.getTopicTitle().isBlank()
                        ? request.getTopicTitle().trim()
                        : "随笔");
        body.setAgentSessionId(request.getSessionId() != null ? request.getSessionId().trim() : "");
        body.setStatus(
                request.getStatus() != null && !request.getStatus().isBlank()
                        ? request.getStatus().trim()
                        : "published");
        NoteDto created = noteService.createNote(body);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.ok(created));
    }

    /** 更新已有笔记；不触发 Agent 回复（与 PUT /notes/{id} 一致）。 */
    @PutMapping("/update-note")
    public ApiResponse<NoteDto> updateNote(@Valid @RequestBody UpdateNoteActionRequest request) {
        NoteWriteRequest body = new NoteWriteRequest();
        body.setTitle(request.getTitle().trim());
        body.setContent(request.getContent().trim());
        if (request.getTopicTitle() != null && !request.getTopicTitle().isBlank()) {
            body.setTopicTitle(request.getTopicTitle().trim());
        }
        if (request.getStatus() != null && !request.getStatus().isBlank()) {
            body.setStatus(request.getStatus().trim());
        }
        body.setRegenerateAgentReply(false);
        return ApiResponse.ok(noteService.updateNote(request.getNoteId().trim(), body));
    }
}
