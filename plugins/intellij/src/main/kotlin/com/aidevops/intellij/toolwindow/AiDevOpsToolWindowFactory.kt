package com.aidevops.intellij.toolwindow

import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.ToolWindow
import com.intellij.openapi.wm.ToolWindowFactory
import com.intellij.ui.content.ContentFactory

class AiDevOpsToolWindowFactory : ToolWindowFactory {

    override fun createToolWindowContent(project: Project, toolWindow: ToolWindow) {
        val analysisPanel = AnalysisPanel(project)
        val deployPanel = DeployPanel(project)
        val logsPanel = LogsPanel(project)

        val contentFactory = ContentFactory.getInstance()
        toolWindow.contentManager.addContent(
            contentFactory.createContent(analysisPanel, "Analysis", false)
        )
        toolWindow.contentManager.addContent(
            contentFactory.createContent(deployPanel, "Deploy", false)
        )
        toolWindow.contentManager.addContent(
            contentFactory.createContent(logsPanel, "Logs & Fix", false)
        )
    }

    override fun shouldBeAvailable(project: Project): Boolean = true
}
