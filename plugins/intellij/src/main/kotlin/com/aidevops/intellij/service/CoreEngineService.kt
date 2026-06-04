package com.aidevops.intellij.service

import com.aidevops.intellij.client.CoreEngineClient
import com.aidevops.intellij.settings.AiDevOpsSettings
import com.intellij.notification.NotificationGroupManager
import com.intellij.notification.NotificationType
import com.intellij.openapi.components.Service
import com.intellij.openapi.diagnostic.logger
import com.intellij.openapi.project.Project
import java.io.File

private val LOG = logger<CoreEngineService>()

@Service(Service.Level.PROJECT)
class CoreEngineService(private val project: Project) {

    private var engineProcess: Process? = null

    val client: CoreEngineClient
        get() = CoreEngineClient(AiDevOpsSettings.instance.coreEnginePort)

    /**
     * Core Engine이 실행 중인지 확인하고, 미실행 시 자동 시작을 시도한다.
     * @return true if engine is reachable
     */
    fun ensureRunning(): Boolean {
        if (client.isRunning()) return true

        val settings = AiDevOpsSettings.instance
        if (!settings.autoStartEngine) {
            notify("Core Engine이 실행되어 있지 않습니다. 수동으로 시작하거나 Settings에서 자동 시작을 활성화하세요.", NotificationType.WARNING)
            return false
        }

        return tryStartEngine(settings)
    }

    private fun tryStartEngine(settings: AiDevOpsSettings): Boolean {
        val cmd = resolveEngineCommand(settings.coreEnginePath)
        if (cmd == null) {
            notify("Core Engine 실행 파일을 찾을 수 없습니다. Settings > AI DevOps에서 경로를 설정하세요.", NotificationType.ERROR)
            return false
        }

        LOG.info("Starting Core Engine: $cmd")
        return runCatching {
            engineProcess = ProcessBuilder(cmd)
                .redirectErrorStream(true)
                .start()
            // 최대 8초 대기
            repeat(8) {
                Thread.sleep(1000)
                if (client.isRunning()) return@runCatching
            }
            if (!client.isRunning()) error("timeout")
        }.onSuccess {
            notify("Core Engine 시작 완료 (포트 ${settings.coreEnginePort})", NotificationType.INFORMATION)
        }.onFailure {
            notify("Core Engine 시작 실패: ${it.message}", NotificationType.ERROR)
        }.isSuccess && client.isRunning()
    }

    private fun resolveEngineCommand(configuredPath: String): String? {
        if (configuredPath.isNotBlank() && File(configuredPath).exists()) return configuredPath
        // PATH에서 aidevops-server 탐색
        val candidates = listOf("aidevops-server", "aidevops-server.exe")
        for (name in candidates) {
            val found = System.getenv("PATH")
                ?.split(File.pathSeparator)
                ?.mapNotNull { dir -> File(dir, name).takeIf { it.canExecute() } }
                ?.firstOrNull()
            if (found != null) return found.absolutePath
        }
        return null
    }

    private fun notify(message: String, type: NotificationType) {
        NotificationGroupManager.getInstance()
            .getNotificationGroup("AI DevOps")
            .createNotification(message, type)
            .notify(project)
    }

    fun stopEngine() {
        engineProcess?.destroy()
        engineProcess = null
    }
}
