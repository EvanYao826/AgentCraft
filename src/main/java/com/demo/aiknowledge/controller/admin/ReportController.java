package com.demo.aiknowledge.controller.admin;

import com.demo.aiknowledge.common.Result;
import com.demo.aiknowledge.dto.ReportRequest;
import com.demo.aiknowledge.dto.ReportResponse;
import com.demo.aiknowledge.service.ReportService;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;

@RestController
@RequestMapping("/api/admin/reports")
@RequiredArgsConstructor
public class ReportController {

    private final ReportService reportService;

    @GetMapping("/generate")
    public Result<ReportResponse> generateReport(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate startDate,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate endDate,
            @RequestParam(required = false, defaultValue = "daily") String reportType,
            @RequestParam(required = false, defaultValue = "10") Integer topN) {

        ReportRequest request = new ReportRequest();
        request.setStartDate(startDate);
        request.setEndDate(endDate);
        request.setReportType(reportType);
        request.setTopN(topN);

        ReportResponse response = reportService.generateReport(request);
        return Result.success(response);
    }

    @GetMapping("/summary")
    public Result<ReportResponse.ReportSummary> getReportSummary(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate startDate,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate endDate,
            @RequestParam(required = false, defaultValue = "daily") String reportType) {

        ReportRequest request = new ReportRequest();
        request.setStartDate(startDate);
        request.setEndDate(endDate);
        request.setReportType(reportType);

        ReportResponse.ReportSummary summary = reportService.getReportSummary(request);
        return Result.success(summary);
    }

    @GetMapping("/hot-questions")
    public Result<ReportResponse.HotQuestionReport> getHotQuestions(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate startDate,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate endDate,
            @RequestParam(required = false, defaultValue = "10") Integer topN) {

        ReportRequest request = new ReportRequest();
        request.setStartDate(startDate);
        request.setEndDate(endDate);
        request.setTopN(topN);

        ReportResponse.HotQuestionReport report = reportService.getHotQuestions(request);
        return Result.success(report);
    }

    @GetMapping("/knowledge-growth")
    public Result<ReportResponse.KnowledgeGrowthReport> getKnowledgeGrowth(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate startDate,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate endDate) {

        ReportRequest request = new ReportRequest();
        request.setStartDate(startDate);
        request.setEndDate(endDate);

        ReportResponse.KnowledgeGrowthReport report = reportService.getKnowledgeGrowth(request);
        return Result.success(report);
    }

    @GetMapping("/agent-performance")
    public Result<ReportResponse.AgentPerformanceReport> getAgentPerformance(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate startDate,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate endDate) {

        ReportRequest request = new ReportRequest();
        request.setStartDate(startDate);
        request.setEndDate(endDate);

        ReportResponse.AgentPerformanceReport report = reportService.getAgentPerformance(request);
        return Result.success(report);
    }

    @GetMapping("/tool-failures")
    public Result<ReportResponse.ToolFailureReport> getToolFailures(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate startDate,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate endDate,
            @RequestParam(required = false, defaultValue = "10") Integer topN) {

        ReportRequest request = new ReportRequest();
        request.setStartDate(startDate);
        request.setEndDate(endDate);
        request.setTopN(topN);

        ReportResponse.ToolFailureReport report = reportService.getToolFailures(request);
        return Result.success(report);
    }
}
