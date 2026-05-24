package com.personalblog.controller;

import com.personalblog.common.ApiResponse;
import com.personalblog.common.PageResult;
import com.personalblog.dto.LifeDto;
import com.personalblog.dto.LifeWriteRequest;
import com.personalblog.dto.ViewRecordResultDto;
import com.personalblog.service.ContentViewService;
import com.personalblog.service.LifeService;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/life")
@RequiredArgsConstructor
public class LifeController {

    private final LifeService lifeService;
    private final ContentViewService contentViewService;

    @GetMapping
    public ApiResponse<PageResult<LifeDto>> listLife(
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String tag,
            @RequestParam(required = false) String yearMonth,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int pageSize,
            @RequestParam(defaultValue = "date_desc") String sort) {
        return ApiResponse.ok(
                lifeService.listLife(keyword, status, tag, yearMonth, page, pageSize, sort));
    }

    @PostMapping
    public ResponseEntity<ApiResponse<LifeDto>> createLife(@RequestBody LifeWriteRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.ok(lifeService.createLife(request)));
    }

    @PostMapping("/{id}/views")
    public ApiResponse<ViewRecordResultDto> recordView(@PathVariable String id, HttpServletRequest request) {
        return ApiResponse.ok(contentViewService.recordLifeView(id, request));
    }

    @PostMapping("/{id}/pin")
    public ApiResponse<LifeDto> pinLife(@PathVariable String id) {
        return ApiResponse.ok(lifeService.pinLife(id));
    }

    @PutMapping("/{id}")
    public ApiResponse<LifeDto> updateLife(@PathVariable String id, @RequestBody LifeWriteRequest request) {
        return ApiResponse.ok(lifeService.updateLife(id, request));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteLife(@PathVariable String id) {
        lifeService.deleteLife(id);
        return ResponseEntity.noContent().build();
    }
}
