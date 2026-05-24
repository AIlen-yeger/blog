package com.personalblog.dto;

import lombok.Data;

import java.util.List;

@Data
public class SearchResultDto {
    private List<NoteDto> notes;
    private List<LifeDto> life;
    private long noteTotal;
    private long lifeTotal;
}
