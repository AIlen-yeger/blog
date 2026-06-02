package com.personalblog.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.personalblog.common.AgentCommentJobStatus;
import com.personalblog.common.ContentStatus;
import com.personalblog.mapper.NoteMapper;
import com.personalblog.config.AgentProperties;
import com.personalblog.config.AgentReplyProperties;
import com.personalblog.entity.ContentAgentCommentJobEntity;
import com.personalblog.entity.NoteEntity;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Optional;

/**
 * 笔记发布后异步请求 Python Agent 生成 Kohaku 评论并入库（任务表幂等）。
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class AgentNoteCommentService {

    private final AgentProperties agentProperties;
    private final AgentReplyProperties agentReplyProperties;
    private final ContentAgentCommentJobService commentJobService;
    private final NoteMapper noteMapper;
    private final ObjectMapper objectMapper;
    private final HttpClient agentHttpClient;

    @Value("${app.agent.ops-token:}")
    private String opsToken;

    @Async
    public void enqueueAfterNoteCreated(NoteEntity note, String agentSessionId) {
        if (!agentReplyProperties.isNoteEnabled()) {
            return;
        }
        if (note == null || note.getId() == null || note.getId().isBlank()) {
            return;
        }
        if (!ContentStatus.PUBLISHED.equals(note.getStatus())) {
            return;
        }
        String content = note.getContent() != null ? note.getContent().trim() : "";
        if (content.isBlank()) {
            return;
        }
        String token = (opsToken == null ? "" : opsToken).trim();
        if (token.isEmpty()) {
            log.warn("[note-comment] skip noteId={} reason=ops-token-not-configured", note.getId());
            return;
        }

        Optional<ContentAgentCommentJobEntity> jobOpt =
                commentJobService.tryEnqueueNoteJob(note, agentSessionId);
        if (jobOpt.isEmpty()) {
            return;
        }
        ContentAgentCommentJobEntity job = jobOpt.get();
        String jobId = job.getJobId();

        int running = commentJobService.markRunning(jobId);
        if (running == 0) {
            log.warn("[note-comment] markRunning skipped jobId={}", jobId);
            return;
        }
        noteMapper.updateAgentReplyMeta(note.getId(), AgentCommentJobStatus.RUNNING, jobId);

        try {
            ObjectNode body = objectMapper.createObjectNode();
            body.put("noteId", note.getId());
            body.put("jobId", jobId);
            body.put("noteTitle", note.getTitle() != null ? note.getTitle() : "");
            body.put("question", content);
            if (job.getSessionId() != null && !job.getSessionId().isBlank()) {
                body.put("sessionId", job.getSessionId());
            }
            if (job.getUserId() > 0) {
                body.put("userId", job.getUserId());
            }
            body.put("limit", 20);

            byte[] bytes = objectMapper.writeValueAsBytes(body);
            URI uri = URI.create(normalizeBaseUrl() + agentProperties.getNoteCommentPath());
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(uri)
                    .timeout(Duration.ofMillis(agentProperties.getNoteCommentReadTimeoutMs()))
                    .header("Content-Type", "application/json; charset=utf-8")
                    .header("X-Ops-Token", token)
                    .POST(HttpRequest.BodyPublishers.ofByteArray(bytes))
                    .build();

            HttpResponse<String> response = agentHttpClient.send(
                    request,
                    HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
            if (response.statusCode() >= 400) {
                String err = truncate(response.body());
                log.warn(
                        "[note-comment] python error noteId={} jobId={} status={} body={}",
                        note.getId(),
                        jobId,
                        response.statusCode(),
                        err);
                commentJobService.markFailed(jobId, note.getId(), "HTTP " + response.statusCode() + ": " + err);
                return;
            }

            boolean saved = parseSavedFlag(response.body());
            if (!saved) {
                commentJobService.markFailed(jobId, note.getId(), "Python 未成功保存 agent_reply");
                log.warn("[note-comment] not saved noteId={} jobId={} body={}", note.getId(), jobId, truncate(response.body()));
            } else {
                log.info("[note-comment] ok noteId={} jobId={}", note.getId(), jobId);
            }
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            commentJobService.markFailed(jobId, note.getId(), "interrupted");
            log.warn("[note-comment] interrupted noteId={} jobId={}", note.getId(), jobId);
        } catch (Exception ex) {
            commentJobService.markFailed(jobId, note.getId(), ex.getMessage());
            log.warn("[note-comment] failed noteId={} jobId={} err={}", note.getId(), jobId, ex.getMessage());
        }
    }

    private boolean parseSavedFlag(String body) {
        if (body == null || body.isBlank()) {
            return false;
        }
        try {
            JsonNode root = objectMapper.readTree(body);
            if (root.has("saved")) {
                return root.get("saved").asBoolean(false);
            }
        } catch (Exception ignored) {
            /* 非 JSON */
        }
        return false;
    }

    private String normalizeBaseUrl() {
        String base = agentProperties.getBaseUrl().trim();
        if (base.endsWith("/")) {
            return base.substring(0, base.length() - 1);
        }
        return base;
    }

    private static String truncate(String s) {
        if (s == null) {
            return "";
        }
        String t = s.trim();
        return t.length() > 300 ? t.substring(0, 300) + "…" : t;
    }
}
