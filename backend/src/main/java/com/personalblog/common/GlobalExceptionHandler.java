package com.personalblog.common;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.personalblog.util.AgentSseWriter;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.io.IOException;

@RestControllerAdvice
@RequiredArgsConstructor
public class GlobalExceptionHandler {

    private final ObjectMapper objectMapper;

    @ExceptionHandler(BusinessException.class)
    public Object handleBusiness(
            BusinessException ex,
            HttpServletRequest request,
            HttpServletResponse response) throws IOException {
        if (prefersEventStream(request) && !response.isCommitted()) {
            writeSseBusinessError(response, ex);
            return null;
        }
        return jsonBusiness(ex);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public Object handleValidation(
            MethodArgumentNotValidException ex,
            HttpServletRequest request,
            HttpServletResponse response) throws IOException {
        FieldError fieldError = ex.getBindingResult().getFieldError();
        String message = fieldError != null ? fieldError.getDefaultMessage() : "参数校验失败";
        if (prefersEventStream(request) && !response.isCommitted()) {
            writeSseBusinessError(response, new BusinessException(ErrorCode.TITLE_REQUIRED, message));
            return null;
        }
        return ResponseEntity.badRequest()
                .contentType(MediaType.APPLICATION_JSON)
                .body(ApiResponse.fail(400, message));
    }

    @ExceptionHandler(Exception.class)
    public Object handleGeneric(
            Exception ex,
            HttpServletRequest request,
            HttpServletResponse response) throws IOException {
        if (prefersEventStream(request) && !response.isCommitted()) {
            writeSseBusinessError(
                    response,
                    new BusinessException(ErrorCode.INTERNAL_ERROR, "服务内部错误，请稍后重试"));
            return null;
        }
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .contentType(MediaType.APPLICATION_JSON)
                .body(ApiResponse.fail(ErrorCode.INTERNAL_ERROR));
    }

    private ResponseEntity<ApiResponse<Void>> jsonBusiness(BusinessException ex) {
        ErrorCode ec = ex.getErrorCode();
        HttpStatus status = mapStatus(ec);
        String message = ex.getMessage();
        if (message == null || message.isBlank()) {
            message = ec.getMessage();
        }
        return ResponseEntity.status(status)
                .contentType(MediaType.APPLICATION_JSON)
                .body(ApiResponse.fail(ec.getCode(), message));
    }

    private void writeSseBusinessError(HttpServletResponse response, BusinessException ex)
            throws IOException {
        response.resetBuffer();
        response.setStatus(HttpServletResponse.SC_OK);
        response.setContentType(MediaType.TEXT_EVENT_STREAM_VALUE);
        response.setCharacterEncoding("UTF-8");
        response.setHeader("Cache-Control", "no-cache, no-transform");
        response.setHeader("Connection", "keep-alive");
        response.setHeader("X-Accel-Buffering", "no");
        AgentSseWriter.writeError(objectMapper, response.getOutputStream(), ex);
    }

    private static boolean prefersEventStream(HttpServletRequest request) {
        String accept = request.getHeader(HttpHeaders.ACCEPT);
        return accept != null && accept.contains(MediaType.TEXT_EVENT_STREAM_VALUE);
    }

    private HttpStatus mapStatus(ErrorCode ec) {
        return switch (ec) {
            case UNAUTHORIZED -> HttpStatus.UNAUTHORIZED;
            case FORBIDDEN, QUIET_HOURS -> HttpStatus.FORBIDDEN;
            case NOTE_NOT_FOUND, LIFE_NOT_FOUND, ACCOUNT_NOT_REGISTERED -> HttpStatus.NOT_FOUND;
            case EMAIL_ALREADY_REGISTERED -> HttpStatus.CONFLICT;
            case CODE_SEND_TOO_FREQUENT, CODE_DAILY_LIMIT -> HttpStatus.TOO_MANY_REQUESTS;
            case MAIL_SEND_FAILED -> HttpStatus.INTERNAL_SERVER_ERROR;
            case INVALID_QQ_EMAIL, PASSWORD_TOO_SHORT, WRONG_PASSWORD, INVALID_VERIFICATION_CODE,
                 TITLE_REQUIRED, TOPIC_NOT_FOUND -> HttpStatus.BAD_REQUEST;
            default -> HttpStatus.BAD_REQUEST;
        };
    }
}
