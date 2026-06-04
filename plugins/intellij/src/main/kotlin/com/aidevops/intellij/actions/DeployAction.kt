package com.aidevops.intellij.actions

import com.aidevops.intellij.service.CoreEngineService
import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.ui.Messages
import com.intellij.openapi.wm.ToolWindowManager

class DeployAction : AnAction() {

    override fun getActionUpdateThread() = ActionUpdateThread.BGT

    override fun update(e: AnActionEvent) {
        e.presentation.isEnabled = e.project != null
    }

    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val svc = project.getService(CoreEngineService::class.java)
        if (!svc.ensureRunning()) return

        val servers = runCatching { svc.client.getServers() }.getOrDefault(emptyList())
        if (servers.isEmpty()) {
            Messages.showWarningDialog(project, "등록된 서버가 없습니다. Settings > AI DevOps에서 서버를 등록하세요.", "서버 없음")
            return
        }

        val serverNames = servers.map { "${it.name} (${it.host}:${it.port})" }.toTypedArray()
        val choice = Messages.showChooseDialog(
            project, "배포할 서버를 선택하세요:", "Deploy",
            serverNames, serverNames[0], Messages.getQuestionIcon()
        )
        if (choice < 0) return
        val server = servers[choice]

        // Tool Window의 Deploy 탭으로 이동
        ApplicationManager.getApplication().invokeLater {
            val tw = ToolWindowManager.getInstance(project).getToolWindow("AI DevOps")
            tw?.activate {
                tw.contentManager.findContent("Deploy")?.let {
                    tw.contentManager.setSelectedContent(it)
                }
            }
            Messages.showInfoMessage(
                project,
                "Deploy 탭에서 ${server.name} 서버를 선택하고 배포를 시작하세요.",
                "Deploy"
            )
        }
    }
}
