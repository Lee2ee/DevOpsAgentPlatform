package com.aidevops.intellij.client

data class ScanResult(
    val language: String = "unknown",
    val framework: String = "unknown",
    val buildTool: String = "unknown",
    val javaVersion: String? = null,
    val appPort: Int? = null,
    val requiredServices: List<String> = emptyList(),
    val warnings: List<String> = emptyList(),
)

data class ScanResponse(
    val projectId: String,
    val scanResult: ScanResult,
)

data class GenerationResponse(
    val generationId: String,
    val warnings: List<String> = emptyList(),
)

data class DeployStartResponse(
    val deploymentId: String,
    val status: String,
    val wsUrl: String,
)

data class DeployStep(
    val name: String,
    val status: String,
    val durationSec: Double? = null,
    val logOutput: String = "",
)

data class DeployStatusResponse(
    val deploymentId: String,
    val status: String,
    val steps: List<DeployStep> = emptyList(),
    val serviceUrl: String? = null,
    val errorMessage: String? = null,
)

data class DetectedError(
    val name: String,
    val severity: String,
    val category: String,
    val suggestion: String,
    val matchedLines: List<String> = emptyList(),
)

data class AnalyzeResponse(
    val analysisId: String,
    val overallSeverity: String,
    val detectedErrors: List<DetectedError> = emptyList(),
    val aiSummary: String = "",
)

data class PatchSuggestion(
    val id: String,
    val filePath: String,
    val description: String,
    val diffContent: String,
    val confidence: Double,
)

data class ServerInfo(
    val id: String,
    val name: String,
    val host: String,
    val port: Int,
    val username: String,
)

data class DeployEvent(
    val event: String,
    val data: Map<String, Any>,
)
