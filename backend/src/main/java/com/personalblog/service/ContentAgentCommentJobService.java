package com.personalblog.service;

import com.personalblog.common.AgentCommentJobStatus;
import com.personalblog.entity.ContentAgentCommentJobEntity;
import com.personalblog.entity.NoteEntity;
import com.personalblog.mapper.ContentAgentCommentJobMapper;
import com.personalblog.mapper.NoteMapper;
import com.personalblog.util.AgentContentHash;
import com.personalblog.util.IdGenerator;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Optional;

@Service
@RequiredArgsConstructor
@Slf4j
public class ContentAgentCommentJobService {

    public static final String CONTENT_TYPE_NOTE = "note";

    private final ContentAgentCommentJobMapper jobMapper;
    private final NoteMapper noteMapper;
    private final SiteOwnerUserService siteOwnerUserService;

    /**
     * 为笔记创建或复用任务；若无需再调 Python 则返回 empty。
     */
    @Transactional
    public Optional<ContentAgentCommentJobEntity> tryEnqueueNoteJob(NoteEntity note, String agentSessionId) {
        String contentHash = AgentContentHash.sha256NoteContent(note.getTitle(), note.getContent());
        String idempotencyKey = AgentContentHash.idempotencyKey(CONTENT_TYPE_NOTE, note.getId(), contentHash);

        ContentAgentCommentJobEntity existing = jobMapper.selectByIdempotencyKey(idempotencyKey);
        if (existing != null) {
            return resolveExistingNoteJob(existing, note.getId());
        }

        String jobId = IdGenerator.agentCommentJobId();
        long ownerId = siteOwnerUserService.resolveSiteOwnerUserId();
        ContentAgentCommentJobEntity job = new ContentAgentCommentJobEntity();
        job.setContentType(CONTENT_TYPE_NOTE);
        job.setContentId(note.getId());
        job.setJobId(jobId);
        job.setIdempotencyKey(idempotencyKey);
        job.setContentHash(contentHash);
        String sessionId = agentSessionId != null ? agentSessionId.trim() : "";
        job.setSessionId(sessionId.isBlank() ? null : sessionId);
        job.setUserId(ownerId);
        job.setStatus(AgentCommentJobStatus.PENDING);
        job.setRequestedAt(LocalDateTime.now());

        try {
            jobMapper.insert(job);
        } catch (DuplicateKeyException ex) {
            log.info("[agent-job] duplicate idempotency noteId={} key={}", note.getId(), idempotencyKey);
            ContentAgentCommentJobEntity raced = jobMapper.selectByIdempotencyKey(idempotencyKey);
            if (raced == null) {
                return Optional.empty();
            }
            return resolveExistingNoteJob(raced, note.getId());
        }

        noteMapper.resetAgentReplyForRegeneration(
                note.getId(), AgentCommentJobStatus.PENDING, jobId);
        return Optional.of(job);
    }

    public int markRunning(String jobId) {
        return jobMapper.markRunning(jobId);
    }

    @Transactional
    public boolean completeNoteReply(String jobId, String noteId, String agentReply) {
        ContentAgentCommentJobEntity job = jobMapper.selectByJobId(jobId);
        if (job == null) {
            return false;
        }
        if (!CONTENT_TYPE_NOTE.equals(job.getContentType()) || !noteId.equals(job.getContentId())) {
            return false;
        }
        if (AgentCommentJobStatus.DONE.equals(job.getStatus())) {
            String prev = job.getAgentReply() != null ? job.getAgentReply().trim() : "";
            return prev.equals(agentReply.trim());
        }
        if (!AgentCommentJobStatus.RUNNING.equals(job.getStatus())) {
            return false;
        }
        int updated = jobMapper.markDone(jobId, agentReply);
        if (updated == 0) {
            return false;
        }
        noteMapper.updateAgentReplyComplete(noteId, agentReply, jobId);
        return true;
    }

    public void markFailed(String jobId, String noteId, String errorMessage) {
        if (jobId == null || jobId.isBlank()) {
            return;
        }
        jobMapper.markFailed(jobId, truncateError(errorMessage));
        if (noteId != null && !noteId.isBlank()) {
            noteMapper.updateAgentReplyMeta(noteId, AgentCommentJobStatus.FAILED, jobId);
        }
    }

    private Optional<ContentAgentCommentJobEntity> resolveExistingNoteJob(
            ContentAgentCommentJobEntity existing,
            String noteId) {
        String status = existing.getStatus();
        if (AgentCommentJobStatus.DONE.equals(status)) {
            syncNoteFromDoneJob(existing, noteId);
            return Optional.empty();
        }
        if (AgentCommentJobStatus.PENDING.equals(status) || AgentCommentJobStatus.RUNNING.equals(status)) {
            log.info("[agent-job] skip in-flight noteId={} jobId={} status={}", noteId, existing.getJobId(), status);
            return Optional.empty();
        }
        if (AgentCommentJobStatus.FAILED.equals(status)) {
            String newJobId = IdGenerator.agentCommentJobId();
            existing.setJobId(newJobId);
            existing.setStatus(AgentCommentJobStatus.PENDING);
            existing.setRequestedAt(LocalDateTime.now());
            existing.setTraceId(null);
            int n = jobMapper.resetFailedToPending(existing);
            if (n == 0) {
                return Optional.empty();
            }
            noteMapper.resetAgentReplyForRegeneration(
                    noteId, AgentCommentJobStatus.PENDING, newJobId);
            return Optional.of(existing);
        }
        return Optional.empty();
    }

    private void syncNoteFromDoneJob(ContentAgentCommentJobEntity job, String noteId) {
        String reply = job.getAgentReply();
        if (reply == null || reply.isBlank()) {
            return;
        }
        noteMapper.updateAgentReplyComplete(noteId, reply, job.getJobId());
    }

    private static String truncateError(String message) {
        if (message == null) {
            return "unknown";
        }
        String t = message.trim();
        return t.length() > 500 ? t.substring(0, 500) : t;
    }
}
