package com.personalblog.controller;

import com.personalblog.common.ApiResponse;
import com.personalblog.config.AgentReplyProperties;
import com.personalblog.dto.AgentReplyOwnerOnlyRequest;
import com.personalblog.dto.AgentReplySettingsDto;
import com.personalblog.dto.ArchiveMonthDto;
import com.personalblog.dto.TagCountDto;
import com.personalblog.security.AdminGuard;
import com.personalblog.service.ContentMetaService;
import com.personalblog.service.ProfileService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/meta")
@RequiredArgsConstructor
public class MetaController {

    private final ContentMetaService contentMetaService;
    private final AgentReplyProperties agentReplyProperties;
    private final ProfileService profileService;
    private final AdminGuard adminGuard;

    @GetMapping("/tags")
    public ApiResponse<List<TagCountDto>> listTags() {
        return ApiResponse.ok(contentMetaService.listTags());
    }

    @GetMapping("/archive-months")
    public ApiResponse<List<ArchiveMonthDto>> listArchiveMonths() {
        return ApiResponse.ok(contentMetaService.listArchiveMonths());
    }

    /** Kohaku 自动回复开关（笔记 / 生活记录分别控制） */
    @GetMapping("/agent-reply-settings")
    public ApiResponse<AgentReplySettingsDto> agentReplySettings() {
        return ApiResponse.ok(buildAgentReplySettings());
    }

    /** 管理员更新「蕾西亚回复仅个人可见」 */
    @PutMapping("/agent-reply-settings")
    public ApiResponse<AgentReplySettingsDto> updateAgentReplySettings(
            @RequestBody AgentReplyOwnerOnlyRequest request) {
        adminGuard.requireAdmin();
        profileService.setAgentReplyOwnerOnly(request.isOwnerOnlyVisible());
        return ApiResponse.ok(buildAgentReplySettings());
    }

    private AgentReplySettingsDto buildAgentReplySettings() {
        return AgentReplySettingsDto.builder()
                .noteEnabled(agentReplyProperties.isNoteEnabled())
                .lifeEnabled(agentReplyProperties.isLifeEnabled())
                .previewMaxChars(agentReplyProperties.getPreviewMaxChars())
                .ownerOnlyVisible(profileService.isAgentReplyOwnerOnly())
                .build();
    }
}
