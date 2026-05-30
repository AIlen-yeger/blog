package com.personalblog.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.personalblog.common.BusinessException;
import com.personalblog.common.ErrorCode;
import com.personalblog.config.AgentProperties;
import com.personalblog.dto.AgentPythonChatRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.UncheckedIOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;

/**
 * 方案 A：透传 Python Agent 的 SSE 流，边读边写并 flush，避免整段缓冲。
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class AgentProxyService {

    private static final int COPY_BUFFER_SIZE = 4096;

    private final AgentProperties agentProperties;
    private final ObjectMapper objectMapper;
    private final HttpClient agentHttpClient;

    public void streamChat(AgentPythonChatRequest payload, OutputStream clientOut) throws IOException {
        String body = objectMapper.writeValueAsString(payload);
        if (body == null || body.isBlank()) {
            throw new BusinessException(ErrorCode.INTERNAL_ERROR, "Agent 请求体为空");
        }
        byte[] bodyBytes = body.getBytes(StandardCharsets.UTF_8);
        URI uri = URI.create(normalizeBaseUrl() + agentProperties.getChatPath());
        log.info("[agent] upstream POST uri={} bodyBytes={}", uri, bodyBytes.length);
        log.debug("[agent] upstream body={}", body);

        HttpRequest request = HttpRequest.newBuilder()
                .uri(uri)
                .timeout(Duration.ofMillis(agentProperties.getReadTimeoutMs()))
                .version(HttpClient.Version.HTTP_1_1)
                .header("Content-Type", "application/json; charset=utf-8")
                .header("Accept", "text/event-stream")
                .POST(HttpRequest.BodyPublishers.ofByteArray(bodyBytes))
                .build();

        HttpResponse<InputStream> response;
        try {
            response = agentHttpClient.send(request, HttpResponse.BodyHandlers.ofInputStream());
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new BusinessException(ErrorCode.INTERNAL_ERROR, "Agent 服务中断");
        } catch (IOException ex) {
            log.warn("[agent] upstream unreachable uri={} err={}", uri, ex.getMessage());
            throw new BusinessException(ErrorCode.INTERNAL_ERROR, "Agent 服务不可用，请稍后重试");
        }

        int status = response.statusCode();
        if (status >= 400) {
            String errBody;
            try (InputStream errStream = response.body()) {
                errBody = new String(errStream.readAllBytes(), StandardCharsets.UTF_8);
            }
            log.warn("[agent] upstream error status={} body={}", status, errBody);
            String detail = summarizeUpstreamError(errBody);
            throw new BusinessException(ErrorCode.INTERNAL_ERROR, detail);
        }

        String contentType = response.headers().firstValue("Content-Type").orElse("");
        if (!contentType.contains("text/event-stream")) {
            log.warn("[agent] upstream did not return SSE content-type={}", contentType);
        }

        try (InputStream upstream = response.body()) {
            pipeWithFlush(upstream, clientOut);
        }
    }

    private void pipeWithFlush(InputStream upstream, OutputStream clientOut) throws IOException {
        byte[] buffer = new byte[COPY_BUFFER_SIZE];
        int read;
        while ((read = upstream.read(buffer)) != -1) {
            clientOut.write(buffer, 0, read);
            clientOut.flush();
        }
    }

    private String normalizeBaseUrl() {
        String base = agentProperties.getBaseUrl().trim();
        if (base.endsWith("/")) {
            return base.substring(0, base.length() - 1);
        }
        return base;
    }

    private String summarizeUpstreamError(String errBody) {
        if (errBody == null || errBody.isBlank()) {
            return "Agent 服务返回错误，请检查 Python 服务是否已启动";
        }
        try {
            var node = objectMapper.readTree(errBody);
            if (node.has("message")) {
                return node.get("message").asText("Agent 返回错误");
            }
            if (node.has("detail")) {
                var detail = node.get("detail");
                if (detail.isTextual()) {
                    return detail.asText("Agent 返回错误");
                }
                if (detail.isArray() && !detail.isEmpty()) {
                    var first = detail.get(0);
                    if (first.has("msg")) {
                        String msg = first.get("msg").asText();
                        if (first.has("loc") && first.get("loc").isArray()) {
                            String loc = first.get("loc").toString();
                            return msg + " " + loc;
                        }
                        return msg;
                    }
                }
            }
        } catch (Exception ignored) {
            /* 非 JSON 响应 */
        }
        String trimmed = errBody.trim();
        return trimmed.length() > 200 ? trimmed.substring(0, 200) + "…" : trimmed;
    }
}
