package com.aidevops.intellij.actions

import com.aidevops.intellij.service.CoreEngineService
import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.ui.Messages

class GenerateCicdAction : AnAction() {

    override fun getActionUpdateThread() = ActionUpdateThread.BGT

    override fun update(e: AnActionEvent) {
        e.presentation.isEnabled = e.project != null
    }

    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val svc = project.getService(CoreEngineService::class.java)
        if (!svc.ensureRunning()) return

        val platforms = arrayOf("github_actions", "gitlab_ci", "jenkins", "azure_devops")
        val choice = Messages.showChooseDialog(
            project, "CI/CD 플랫폼을 선택하세요:", "Generate CI/CD Pipeline",
            platforms, platforms[0], Messages.getQuestionIcon()
        )
        if (choice < 0) return
        val platform = platforms[choice]
        val projectPath = project.basePath ?: return

        ApplicationManager.getApplication().executeOnPooledThread {
            runCatching {
                val scanResp = svc.client.scanProject(projectPath)
                val pid = scanResp.projectId
                val genResp = svc.client.generateCicd(pid, platform)
                svc.client.saveCicd(pid, genResp.generationId)
                ApplicationManager.getApplication().invokeLater {
                    Messages.showInfoMessage(project, "$platform 파이프라인이 생성되었습니다.", "CI/CD 생성 완료")
                }
            }.onFailure { ex ->
                ApplicationManager.getApplication().invokeLater {
                    Messages.showErrorDialog(project, "생성 실패: ${ex.message}", "오류")
                }
            }
        }
    }
}
