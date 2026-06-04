package com.aidevops.intellij.toolwindow

import com.aidevops.intellij.client.DeployEvent
import com.aidevops.intellij.client.ServerInfo
import com.aidevops.intellij.service.CoreEngineService
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.project.Project
import com.intellij.ui.components.JBScrollPane
import com.intellij.util.ui.JBUI
import okhttp3.WebSocket
import java.awt.BorderLayout
import java.awt.FlowLayout
import java.awt.Font
import javax.swing.*

class DeployPanel(private val project: Project) : JPanel(BorderLayout()) {

    private val serverCombo = JComboBox<ServerInfo>()
    private val strategyCombo = JComboBox(arrayOf("local_build", "remote_build"))
    private val deployBtn = JButton("Deploy")
    private val refreshBtn = JButton("↻")
    private val statusLabel = JLabel("대기 중")
    private val logArea = JTextArea().apply {
        isEditable = false
        font = Font(Font.MONOSPACED, Font.PLAIN, 11)
        background = java.awt.Color(30, 30, 30)
        foreground = java.awt.Color(200, 200, 200)
        lineWrap = true
        wrapStyleWord = true
    }

    private var activeWs: WebSocket? = null
    private var currentProjectId: String? = null

    init {
        border = JBUI.Borders.empty(8)

        // 상단 컨트롤
        val controls = JPanel(FlowLayout(FlowLayout.LEFT)).apply {
            add(JLabel("서버:"))
            add(serverCombo.apply { preferredSize = java.awt.Dimension(180, 24) })
            add(refreshBtn.apply { addActionListener { loadServers() } })
            add(JLabel("전략:"))
            add(strategyCombo)
            add(deployBtn.apply { addActionListener { doDeploy() } })
            add(statusLabel)
        }
        add(controls, BorderLayout.NORTH)
        add(JBScrollPane(logArea), BorderLayout.CENTER)

        // 렌더러: ServerInfo → 이름 표시
        serverCombo.renderer = object : DefaultListCellRenderer() {
            override fun getListCellRendererComponent(list: JList<*>, value: Any?, index: Int, isSelected: Boolean, cellHasFocus: Boolean): java.awt.Component {
                super.getListCellRendererComponent(list, value, index, isSelected, cellHasFocus)
                text = (value as? ServerInfo)?.let { "${it.name} (${it.host}:${it.port})" } ?: "서버 없음"
                return this
            }
        }

        loadServers()
    }

    fun setProjectId(id: String) { currentProjectId = id }

    private fun loadServers() {
        val svc = project.getService(CoreEngineService::class.java)
        if (!svc.ensureRunning()) return
        ApplicationManager.getApplication().executeOnPooledThread {
            runCatching {
                val servers = svc.client.getServers()
                SwingUtilities.invokeLater {
                    serverCombo.removeAllItems()
                    servers.forEach { serverCombo.addItem(it) }
                    if (servers.isEmpty()) statusLabel.text = "등록된 서버 없음"
                }
            }
        }
    }

    private fun doDeploy() {
        val pid = currentProjectId ?: run {
            statusLabel.text = "먼저 Analysis 탭에서 프로젝트를 스캔하세요"
            return
        }
        val server = serverCombo.selectedItem as? ServerInfo ?: run {
            statusLabel.text = "서버를 선택하세요"
            return
        }
        val strategy = strategyCombo.selectedItem as String
        val svc = project.getService(CoreEngineService::class.java)

        logArea.text = ""
        deployBtn.isEnabled = false
        statusLabel.text = "배포 시작 중..."
        activeWs?.cancel()

        ApplicationManager.getApplication().executeOnPooledThread {
            runCatching {
                val resp = svc.client.startDeploy(pid, server.id, strategy)
                SwingUtilities.invokeLater { statusLabel.text = "배포 진행 중..." }

                activeWs = svc.client.subscribeDeployProgress(
                    resp.deploymentId,
                    onEvent = { event -> handleEvent(event) },
                    onClose = {
                        SwingUtilities.invokeLater { deployBtn.isEnabled = true }
                    }
                )
            }.onFailure { ex ->
                SwingUtilities.invokeLater {
                    appendLog("[ERR] 배포 시작 실패: ${ex.message}")
                    deployBtn.isEnabled = true
                    statusLabel.text = "실패"
                }
            }
        }
    }

    private fun handleEvent(event: DeployEvent) {
        SwingUtilities.invokeLater {
            when (event.event) {
                "log" -> appendLog(event.data["line"] as? String ?: "")
                "step_start" -> appendLog("[>>] 단계 시작: ${event.data["step"]}")
                "step_done" -> appendLog("[OK] 단계 완료: ${event.data["step"]} (${event.data["duration_sec"]}s)")
                "step_fail" -> appendLog("[FAIL] 단계 실패: ${event.data["step"]} - ${event.data["error"]}")
                "deploy_done" -> {
                    statusLabel.text = "배포 성공!"
                    appendLog("\n[SUCCESS] 서비스 URL: ${event.data["service_url"]}")
                    deployBtn.isEnabled = true
                }
                "deploy_failed" -> {
                    statusLabel.text = "배포 실패"
                    appendLog("\n[FAILED] ${event.data["error"]}")
                    deployBtn.isEnabled = true
                }
            }
        }
    }

    private fun appendLog(line: String) {
        logArea.append("$line\n")
        logArea.caretPosition = logArea.document.length
    }
}
