package com.demo.aiknowledge.dto;

import lombok.Data;
import java.time.LocalDate;

@Data
public class LibraryInspectionRequest {
    private LocalDate startDate;
    private LocalDate endDate;
    private Integer minChunkLength;
    private Integer outdatedDays;
    private Integer unaccessedDays;
    private Double similarityThreshold;
    private Boolean enableDuplicateCheck;
    private Boolean enableQualityCheck;
    private Boolean enableOutdatedCheck;
    private Boolean enableAccessCheck;
}
