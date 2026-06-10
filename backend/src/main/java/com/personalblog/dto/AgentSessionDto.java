package com.personalblog.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class AgentSessionDto {

    private String sessionId;
    private String title;
    private long createdAt;
    private long updatedAt;
}
