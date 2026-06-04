package com.aidevops.intellij.actions

import com.aidevops.intellij.service.CoreEngineService
import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.ui.Messages
import com.intellij.openapi.wm.ToolWindowManager

class ScanProjectAction : AnAction() {

    override fun getActionUpdateThread() = ActionUpdateThread.BGT

    override fun update(e: AnActionEvent) {
        e.presentation.isEnabled = e.project != null
    }

    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val svc = project.getService(CoreEngineService::class.java)
        if (!svc.ensureRunning()) return

        val path = e.getData(CommonDataKeys.VIRTUAL_FILE)?.path
            ?: project.basePath
            ?: run {
                Messages.showErrorDialog(project, "프로젝트 경로를 가져올 수 없습니다.", "오류")
                return
            }

        ApplicationManager.getApplication().executeOnPooledThread {
            runCatching {
                val resp = svc.client.scanProject(path)
                // Tool Window의 Analysis 탭 활성화
                ApplicationManager.getApplication().invokeLater {
                    val tw = ToolWindowManager.getInstance(project).getToolWindow("AI DevOps")
                    tw?.activate(null)
                    Messages.showInfoMessage(
                        project,
                        "스캔 완료!\n언어: ${resp.scanResult.language}\n프레임워크: ${resp.scanResult.framework}\n포트: ${resp.scanResult.appPort ?: "-"}",
                        "프로젝트 스캔 완료"
                    )
                }
            }.onFailure { ex ->
                ApplicationManager.getApplication().invokeLater {
                    Messages.showErrorDialog(project, "스캔 실패: ${ex.message}", "오류")
                }
            }
        }
    }
}
