package com.aidevops.intellij.client

import com.google.gson.FieldNamingPolicy
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import java.util.concurrent.TimeUnit

class CoreEngineClient(port: Int = 8765) {

    private val baseUrl = "http://127.0.0.1:$port/api/v1"
    private val json = "application/json".toMediaType()
    private val gson: Gson = GsonBuilder()
        .setFieldNamingPolicy(FieldNamingPolicy.LOWER_CASE_WITH_UNDERSCORES)
        .create()
    private val http = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .build()

    // ── Health ────────────────────────────────────────────────

    fun isRunning(): Boolean = runCatching {
        val req = Request.Builder().url("$baseUrl/health").get().build()
        http.newCall(req).execute().use { it.isSuccessful }
    }.getOrDefault(false)

    // ── Projects ──────────────────────────────────────────────

    fun scanProject(path: String): ScanResponse {
        val body = """{"path":"$path","use_ai":true}"""
        return post("/projects/scan", body)
    }

    fun getProjects(): List<Map<String, Any>> {
        return get<Map<String, Any>>("/projects").let {
            @Suppress("UNCHECKED_CAST")
            (it["projects"] as? List<Map<String, Any>>) ?: emptyList()
        }
    }

    // ── Docker ────────────────────────────────────────────────

    fun generateDocker(projectId: String, registry: String = ""): GenerationResponse =
        post("/docker/generate", """{"project_id":"$projectId","registry":"$registry"}""")

    fun saveDocker(projectId: String, generationId: String): Map<String, Any> =
        post("/docker/save", """{"project_id":"$projectId","generation_id":"$generationId"}""")

    // ── CI/CD ─────────────────────────────────────────────────

    fun generateCicd(projectId: String, platform: String): GenerationResponse =
        post("/cicd/generate", """{"project_id":"$projectId","platform":"$platform","options":{}}""")

    fun saveCicd(projectId: String, generationId: String): Map<String, Any> =
        post("/cicd/save", """{"project_id":"$projectId","generation_id":"$generationId"}""")

    // ── Deploy ────────────────────────────────────────────────

    fun startDeploy(
        projectId: String,
        serverId: String,
        strategy: String = "local_build",
        autoRollback: Boolean = true,
        healthCheckUrl: String? = null,
    ): DeployStartResponse {
        val hcu = if (healthCheckUrl != null) """"health_check_url":"$healthCheckUrl",""" else ""
        val body = """
            {"project_id":"$projectId","server_id":"$serverId","strategy":"$strategy",
             "options":{${hcu}"auto_rollback":$autoRollback}}
        """.trimIndent()
        return post("/deploy", body)
    }

    fun getDeployment(deploymentId: String): DeployStatusResponse =
        get("/deploy/$deploymentId")

    fun subscribeDeployProgress(
        deploymentId: String,
        onEvent: (DeployEvent) -> Unit,
        onClose: () -> Unit = {},
    ): WebSocket {
        val port = baseUrl.substringAfter("127.0.0.1:").substringBefore("/")
        val url = "ws://127.0.0.1:$port/api/v1/ws/deploy/$deploymentId"
        val req = Request.Builder().url(url).build()
        return http.newWebSocket(req, object : WebSocketListener() {
            override fun onMessage(webSocket: WebSocket, text: String) {
                runCatching {
                    @Suppress("UNCHECKED_CAST")
                    val parsed = gson.fromJson(text, Map::class.java) as Map<String, Any>
                    val event = parsed["event"] as? String ?: return
                    @Suppress("UNCHECKED_CAST")
                    val data = parsed["data"] as? Map<String, Any> ?: emptyMap()
                    onEvent(DeployEvent(event, data))
                }
            }
            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) = onClose()
            override fun onFailure(webSocket: WebSocket, t: Throwable, response: okhttp3.Response?) = onClose()
        })
    }

    // ── Analyze ───────────────────────────────────────────────

    fun analyzeLog(logText: String, useAi: Boolean = false): AnalyzeResponse {
        val escaped = logText.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")
        return post("/analyze", """{"log_text":"$escaped","use_ai":$useAi}""")
    }

    fun analyzeDeployment(deploymentId: String, useAi: Boolean = true): AnalyzeResponse =
        post("/analyze", """{"deployment_id":"$deploymentId","use_ai":$useAi}""")

    fun generatePatches(analysisId: String, useAi: Boolean = false): List<PatchSuggestion> {
        val raw = postRaw("/analyze/$analysisId/patch", """{"use_ai":$useAi}""")
        return gson.fromJson(raw, Array<PatchSuggestion>::class.java).toList()
    }

    // ── Servers ───────────────────────────────────────────────

    fun getServers(): List<ServerInfo> {
        val raw = getRaw("/config/servers")
        return gson.fromJson(raw, Array<ServerInfo>::class.java).toList()
    }

    // ── Internal helpers ──────────────────────────────────────

    private inline fun <reified T> get(path: String): T {
        val req = Request.Builder().url("$baseUrl$path").get().build()
        val body = http.newCall(req).execute().use { resp ->
            check(resp.isSuccessful) { "GET $path failed: ${resp.code}" }
            resp.body!!.string()
        }
        return gson.fromJson(body, T::class.java)
    }

    private fun getRaw(path: String): String {
        val req = Request.Builder().url("$baseUrl$path").get().build()
        return http.newCall(req).execute().use { resp ->
            check(resp.isSuccessful) { "GET $path failed: ${resp.code}" }
            resp.body!!.string()
        }
    }

    private inline fun <reified T> post(path: String, bodyJson: String): T {
        val raw = postRaw(path, bodyJson)
        return gson.fromJson(raw, T::class.java)
    }

    private fun postRaw(path: String, bodyJson: String): String {
        val req = Request.Builder()
            .url("$baseUrl$path")
            .post(bodyJson.toRequestBody(json))
            .build()
        return http.newCall(req).execute().use { resp ->
            check(resp.isSuccessful) { "POST $path failed: ${resp.code} ${resp.body?.string()}" }
            resp.body!!.string()
        }
    }
}
