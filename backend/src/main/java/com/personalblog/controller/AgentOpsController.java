package com.personalblog.controller;

import com.personalblog.common.ApiResponse;
import com.personalblog.common.BusinessException;
import com.personalblog.common.ErrorCode;
import com.personalblog.dto.NoteAgentReplyRequest;
import com.personalblog.dto.QqBlogTokenDto;
import com.personalblog.dto.QqBlogTokenRequest;
import com.personalblog.mapper.NoteMapper;
import com.personalblog.service.AgentQqBridgeService;
import com.personalblog.service.ContentAgentCommentJobService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Agent 运维接口（不对前端开放）：供 Python QQ 桥接等内网服务调用。
 */
@RestController
@RequestMapping("/agent/ops")
@RequiredArgsConstructor
public class AgentOpsController {

    private final AgentQqBridgeService agentQqBridgeService;
    private final NoteMapper noteMapper;
    private final ContentAgentCommentJobService commentJobService;

    @Value("${app.agent.ops-token:}")
    private String opsToken;

    @PostMapping("/notes/{noteId}/agent-reply")
    public ApiResponse<Void> saveNoteAgentReply(
            @RequestHeader(value = "X-Ops-Token", required = false) String xOpsToken,
            @PathVariable String noteId,
            @RequestBody NoteAgentReplyRequest request) {
        requireOpsToken(xOpsToken);
        if (noteMapper.countById(noteId) == 0) {
            throw new BusinessException(ErrorCode.NOTE_NOT_FOUND);
        }
        String jobId = request != null && request.getJobId() != null ? request.getJobId().trim() : "";
        String reply = request != null && request.getAgentReply() != null
                ? request.getAgentReply().trim()
                : "";
        if (jobId.isBlank()) {
            throw new BusinessException(ErrorCode.INTERNAL_ERROR, "jobId 不能为空");
        }
        if (reply.isBlank()) {
            throw new BusinessException(ErrorCode.INTERNAL_ERROR, "agentReply 不能为空");
        }
        boolean ok = commentJobService.completeNoteReply(jobId, noteId, reply);
        if (!ok) {
            throw new BusinessException(ErrorCode.INTERNAL_ERROR, "任务不存在、状态非法或 noteId 不匹配");
        }
        return ApiResponse.ok(null);
    }

    @PostMapping("/token-for-qq")
    public ApiResponse<QqBlogTokenDto> tokenForQq(
            @RequestHeader(value = "X-Ops-Token", required = false) String xOpsToken,
            @Valid @RequestBody QqBlogTokenRequest request) {
        requireOpsToken(xOpsToken);
        return ApiResponse.ok(agentQqBridgeService.issueTokenForQq(request.getQq()));
    }

    private void requireOpsToken(String provided) {
        String expected = (opsToken == null ? "" : opsToken).trim();
        if (expected.isEmpty() || provided == null || !expected.equals(provided.trim())) {
            throw new BusinessException(ErrorCode.FORBIDDEN);
        }
    }
}
