package com.personalblog.common;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<ApiResponse<Void>> handleBusiness(BusinessException ex) {
        ErrorCode ec = ex.getErrorCode();
        HttpStatus status = mapStatus(ec);
        String message = ex.getMessage();
        if (message == null || message.isBlank()) {
            message = ec.getMessage();
        }
        return ResponseEntity.status(status).body(ApiResponse.fail(ec.getCode(), message));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponse<Void>> handleValidation(MethodArgumentNotValidException ex) {
        FieldError fieldError = ex.getBindingResult().getFieldError();
        String message = fieldError != null ? fieldError.getDefaultMessage() : "参数校验失败";
        return ResponseEntity.badRequest().body(ApiResponse.fail(400, message));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Void>> handleGeneric(Exception ex) {
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ApiResponse.fail(ErrorCode.INTERNAL_ERROR));
    }

    private HttpStatus mapStatus(ErrorCode ec) {
        return switch (ec) {
            case UNAUTHORIZED -> HttpStatus.UNAUTHORIZED;
            case FORBIDDEN -> HttpStatus.FORBIDDEN;
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
