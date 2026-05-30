package com.personalblog.util;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.personalblog.common.BusinessException;
import com.personalblog.common.ErrorCode;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;

/** Agent 聊天 SSE 流内错误输出（异步流中无法走 JSON 全局异常处理器） */
public final class AgentSseWriter {

    private AgentSseWriter() {
    }

    public static void writeError(ObjectMapper objectMapper, OutputStream out, BusinessException ex)
            throws IOException {
        ErrorCode ec = ex.getErrorCode();
        String message = ex.getMessage();
        if (message == null || message.isBlank()) {
            message = ec.getMessage();
        }
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("code", ec.getCode());
        payload.put("message", message);
        String json = objectMapper.writeValueAsString(payload);
        out.write(("data: " + json + "\n\n").getBytes(StandardCharsets.UTF_8));
        out.write("data: [DONE]\n\n".getBytes(StandardCharsets.UTF_8));
        out.flush();
    }
}
