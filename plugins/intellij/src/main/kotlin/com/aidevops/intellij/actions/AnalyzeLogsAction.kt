package com.aidevops.intellij.actions

import com.aidevops.intellij.service.CoreEngineService
import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.ui.Messages
import com.intellij.openapi.wm.ToolWindowManager

class AnalyzeLogsAction : AnAction() {

    override fun getActionUpdateThread() = ActionUpdateThread.BGT

    override fun update(e: AnActionEvent) {
        e.presentation.isEnabled = e.project != null
    }

    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val svc = project.getService(CoreEngineService::class.java)
        if (!svc.ensureRunning()) return

        // Tool Window의 Logs & Fix 탭으로 이동
        ApplicationManager.getApplication().invokeLater {
            val tw = ToolWindowManager.getInstance(project).getToolWindow("AI DevOps")
            tw?.activate {
                tw.contentManager.findContent("Logs & Fix")?.let {
                    tw.contentManager.setSelectedContent(it)
                }
            }
        }
    }
}
