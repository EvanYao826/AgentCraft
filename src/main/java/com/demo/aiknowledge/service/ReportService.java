package com.demo.aiknowledge.service;

import com.demo.aiknowledge.dto.ReportRequest;
import com.demo.aiknowledge.dto.ReportResponse;

public interface ReportService {
    ReportResponse generateReport(ReportRequest request);
    ReportResponse.ReportSummary getReportSummary(ReportRequest request);
    ReportResponse.HotQuestionReport getHotQuestions(ReportRequest request);
    ReportResponse.KnowledgeGrowthReport getKnowledgeGrowth(ReportRequest request);
    ReportResponse.AgentPerformanceReport getAgentPerformance(ReportRequest request);
    ReportResponse.ToolFailureReport getToolFailures(ReportRequest request);
}
