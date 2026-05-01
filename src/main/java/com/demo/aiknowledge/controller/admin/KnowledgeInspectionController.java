package com.demo.aiknowledge.controller.admin;

import com.demo.aiknowledge.common.Result;
import com.demo.aiknowledge.dto.*;
import com.demo.aiknowledge.service.KnowledgeInspectionService;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.Map;

@RestController
@RequestMapping("/api/admin/knowledge-inspection")
@RequiredArgsConstructor
public class KnowledgeInspectionController {

    private final KnowledgeInspectionService knowledgeInspectionService;

    @GetMapping("/unanswered/analyze")
    public Result<UnansweredAnalysisResponse> analyzeUnanswered(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate startDate,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate endDate,
            @RequestParam(defaultValue = "1") Integer minCount,
            @RequestParam(defaultValue = "3") Integer clusterThreshold) {
        
        UnansweredAnalysisRequest request = new UnansweredAnalysisRequest();
        request.setStartDate(startDate);
        request.setEndDate(endDate);
        request.setMinCount(minCount);
        request.setClusterThreshold(clusterThreshold);
        
        UnansweredAnalysisResponse response = knowledgeInspectionService.analyzeUnansweredQuestions(request);
        return Result.success(response);
    }

    @GetMapping("/unanswered/statistics")
    public Result<Map<String, Object>> getUnansweredStatistics() {
        Map<String, Object> stats = knowledgeInspectionService.getUnansweredStatistics();
        return Result.success(stats);
    }

    @PostMapping("/run")
    public Result<UnansweredAnalysisResponse> runInspection(@RequestBody(required = false) UnansweredAnalysisRequest request) {
        if (request == null) {
            request = new UnansweredAnalysisRequest();
        }
        UnansweredAnalysisResponse response = knowledgeInspectionService.analyzeUnansweredQuestions(request);
        return Result.success(response);
    }

    @GetMapping("/library/analyze")
    public Result<LibraryInspectionResponse> analyzeLibrary(
            @RequestParam(required = false) Integer minChunkLength,
            @RequestParam(required = false) Integer outdatedDays,
            @RequestParam(required = false) Integer unaccessedDays,
            @RequestParam(required = false) Double similarityThreshold,
            @RequestParam(required = false) Boolean enableDuplicateCheck,
            @RequestParam(required = false) Boolean enableQualityCheck,
            @RequestParam(required = false) Boolean enableOutdatedCheck,
            @RequestParam(required = false) Boolean enableAccessCheck) {

        LibraryInspectionRequest request = new LibraryInspectionRequest();
        request.setMinChunkLength(minChunkLength);
        request.setOutdatedDays(outdatedDays);
        request.setUnaccessedDays(unaccessedDays);
        request.setSimilarityThreshold(similarityThreshold);
        request.setEnableDuplicateCheck(enableDuplicateCheck);
        request.setEnableQualityCheck(enableQualityCheck);
        request.setEnableOutdatedCheck(enableOutdatedCheck);
        request.setEnableAccessCheck(enableAccessCheck);

        LibraryInspectionResponse response = knowledgeInspectionService.inspectLibrary(request);
        return Result.success(response);
    }

    @GetMapping("/library/statistics")
    public Result<Map<String, Object>> getLibraryStatistics() {
        Map<String, Object> stats = knowledgeInspectionService.getLibraryInspectionStats();
        return Result.success(stats);
    }
}