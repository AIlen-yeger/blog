package com.personalblog.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class AgentSessionTitleRequest {

    @NotBlank(message = "标题不能为空")
    @Size(max = 255, message = "标题过长")
    private String title;
}
