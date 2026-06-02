package com.personalblog.mapper;

import com.personalblog.entity.ContentAgentCommentJobEntity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface ContentAgentCommentJobMapper {

    ContentAgentCommentJobEntity selectByIdempotencyKey(@Param("idempotencyKey") String idempotencyKey);

    ContentAgentCommentJobEntity selectByJobId(@Param("jobId") String jobId);

    int insert(ContentAgentCommentJobEntity job);

    int resetFailedToPending(ContentAgentCommentJobEntity job);

    int markRunning(@Param("jobId") String jobId);

    int markDone(
            @Param("jobId") String jobId,
            @Param("agentReply") String agentReply);

    int markFailed(
            @Param("jobId") String jobId,
            @Param("errorMessage") String errorMessage);
}
