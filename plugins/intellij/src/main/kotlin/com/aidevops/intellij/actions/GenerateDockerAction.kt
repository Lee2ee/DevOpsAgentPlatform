package com.aidevops.intellij.actions

import com.aidevops.intellij.service.CoreEngineService
import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.ui.Messages

class GenerateDockerAction : AnAction() {

    override fun getActionUpdateThread() = ActionUpdateThread.BGT

    override fun update(e: AnActionEvent) {
        e.presentation.isEnabled = e.project != null
    }

    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val svc = project.getService(CoreEngineService::class.java)
        if (!svc.ensureRunning()) return

        val projectPath = project.basePath ?: return

        ApplicationManager.getApplication().executeOnPooledThread {
            runCatching {
                // 1. 스캔
                val scanResp = svc.client.scanProject(projectPath)
                val pid = scanResp.projectId

                // 2. 생성
                val genResp = svc.client.generateDocker(pid)

                // 3. 저장
                svc.client.saveDocker(pid, genResp.generationId)

                ApplicationManager.getApplication().invokeLater {
                    val warningMsg = if (genResp.warnings.isNotEmpty())
                        "\n\n경고:\n${genResp.warnings.joinToString("\n• ", "• ")}"
                    else ""
                    Messages.showInfoMessage(
                        project,
                        "Dockerfile / docker-compose.yml이 프로젝트 루트에 생성되었습니다.$warningMsg",
                        "Docker 파일 생성 완료"
                    )
                }
            }.onFailure { ex ->
                ApplicationManager.getApplication().invokeLater {
                    Messages.showErrorDialog(project, "생성 실패: ${ex.message}", "오류")
                }
            }
        }
    }
}
