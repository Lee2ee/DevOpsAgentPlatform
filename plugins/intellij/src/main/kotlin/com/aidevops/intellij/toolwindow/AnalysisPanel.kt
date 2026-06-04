package com.aidevops.intellij.toolwindow

import com.aidevops.intellij.client.ScanResult
import com.aidevops.intellij.service.CoreEngineService
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.Messages
import com.intellij.ui.components.JBLabel
import com.intellij.ui.components.JBScrollPane
import com.intellij.util.ui.JBUI
import java.awt.BorderLayout
import java.awt.FlowLayout
import java.awt.GridLayout
import javax.swing.*

class AnalysisPanel(private val project: Project) : JPanel(BorderLayout()) {

    private val statusLabel = JBLabel("프로젝트를 스캔하세요.")
    private val resultPanel = JPanel(GridLayout(0, 2, 4, 4)).apply { isVisible = false }
    private val warningArea = JTextArea(3, 40).apply {
        isEditable = false
        lineWrap = true
        wrapStyleWord = true
        font = font.deriveFont(11f)
        foreground = java.awt.Color(255, 200, 0)
        background = background.darker()
    }
    private var lastProjectId: String? = null

    init {
        border = JBUI.Borders.empty(8)
        val topBar = JPanel(FlowLayout(FlowLayout.LEFT)).apply {
            add(JButton("Scan Project").apply {
                addActionListener { doScan() }
            })
            add(JButton("Generate Docker").apply {
                addActionListener { doGenerateDocker() }
                isEnabled = false
                putClientProperty("enableBtn", this)
            })
            add(JButton("Generate CI/CD").apply {
                addActionListener { doGenerateCicd() }
                isEnabled = false
                putClientProperty("enableBtn", this)
            })
        }
        add(topBar, BorderLayout.NORTH)

        val centerPanel = JPanel(BorderLayout(0, 8)).apply {
            border = JBUI.Borders.empty(8, 0, 0, 0)
            add(statusLabel, BorderLayout.NORTH)
            add(JBScrollPane(resultPanel), BorderLayout.CENTER)
            add(JBScrollPane(warningArea).also { it.isVisible = false }, BorderLayout.SOUTH)
        }
        add(centerPanel, BorderLayout.CENTER)
    }

    private fun doScan() {
        val svc = project.getService(CoreEngineService::class.java)
        if (!svc.ensureRunning()) return

        val projectPath = project.basePath ?: run {
            Messages.showErrorDialog(project, "프로젝트 경로를 찾을 수 없습니다.", "Error")
            return
        }

        statusLabel.text = "스캔 중..."
        resultPanel.isVisible = false
        warningArea.text = ""

        ApplicationManager.getApplication().executeOnPooledThread {
            runCatching {
                val resp = svc.client.scanProject(projectPath)
                lastProjectId = resp.projectId
                SwingUtilities.invokeLater { showResult(resp.scanResult) }
            }.onFailure { ex ->
                SwingUtilities.invokeLater {
                    statusLabel.text = "스캔 실패: ${ex.message}"
                }
            }
        }
    }

    private fun showResult(result: ScanResult) {
        resultPanel.removeAll()
        resultPanel.isVisible = true

        fun addRow(label: String, value: String) {
            resultPanel.add(JBLabel("$label:").apply { font = font.deriveFont(java.awt.Font.BOLD) })
            resultPanel.add(JBLabel(value))
        }

        addRow("언어", result.language)
        addRow("프레임워크", result.framework)
        addRow("빌드 도구", result.buildTool)
        addRow("포트", result.appPort?.toString() ?: "-")
        addRow("필요 서비스", result.requiredServices.joinToString(", ").ifEmpty { "-" })

        statusLabel.text = "스캔 완료 (project_id: ${lastProjectId?.take(8)}...)"

        if (result.warnings.isNotEmpty()) {
            warningArea.text = result.warnings.joinToString("\n• ", "경고:\n• ")
            warningArea.parent?.isVisible = true
        }

        // 버튼 활성화
        parent?.components?.filterIsInstance<JPanel>()?.firstOrNull()
            ?.components?.filterIsInstance<JButton>()?.forEach { btn ->
                btn.isEnabled = true
            }

        resultPanel.revalidate()
        resultPanel.repaint()
    }

    private fun doGenerateDocker() {
        val pid = lastProjectId ?: return
        val svc = project.getService(CoreEngineService::class.java)
        ApplicationManager.getApplication().executeOnPooledThread {
            runCatching {
                val resp = svc.client.generateDocker(pid)
                svc.client.saveDocker(pid, resp.generationId)
                SwingUtilities.invokeLater {
                    Messages.showInfoMessage(
                        project,
                        "Dockerfile / docker-compose.yml 생성 완료!\n경고: ${resp.warnings.joinToString(", ").ifEmpty { "없음" }}",
                        "Docker 생성 완료"
                    )
                }
            }.onFailure { ex ->
                SwingUtilities.invokeLater {
                    Messages.showErrorDialog(project, "생성 실패: ${ex.message}", "Error")
                }
            }
        }
    }

    private fun doGenerateCicd() {
        val pid = lastProjectId ?: return
        val svc = project.getService(CoreEngineService::class.java)
        val platforms = arrayOf("github_actions", "gitlab_ci", "jenkins", "azure_devops")
        val choice = Messages.showChooseDialog(
            project, "CI/CD 플랫폼을 선택하세요:", "Generate CI/CD",
            platforms, platforms[0], Messages.getQuestionIcon()
        )
        if (choice < 0) return
        val platform = platforms[choice]

        ApplicationManager.getApplication().executeOnPooledThread {
            runCatching {
                val resp = svc.client.generateCicd(pid, platform)
                svc.client.saveCicd(pid, resp.generationId)
                SwingUtilities.invokeLater {
                    Messages.showInfoMessage(project, "$platform 파이프라인 생성 완료!", "CI/CD 생성 완료")
                }
            }.onFailure { ex ->
                SwingUtilities.invokeLater {
                    Messages.showErrorDialog(project, "생성 실패: ${ex.message}", "Error")
                }
            }
        }
    }
}
