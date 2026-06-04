package com.aidevops.intellij.toolwindow

import com.aidevops.intellij.client.PatchSuggestion
import com.aidevops.intellij.service.CoreEngineService
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.Messages
import com.intellij.ui.components.JBScrollPane
import com.intellij.util.ui.JBUI
import java.awt.BorderLayout
import java.awt.FlowLayout
import java.awt.Font
import javax.swing.*

class LogsPanel(private val project: Project) : JPanel(BorderLayout()) {

    private val logInput = JTextArea(8, 40).apply {
        font = Font(Font.MONOSPACED, Font.PLAIN, 11)
        lineWrap = true
        wrapStyleWord = true
        border = JBUI.Borders.empty(4)
    }
    private val analyzeBtn = JButton("Analyze Logs")
    private val generatePatchBtn = JButton("Generate Patch").apply { isEnabled = false }
    private val resultArea = JTextArea(6, 40).apply {
        isEditable = false
        font = Font(Font.MONOSPACED, Font.PLAIN, 11)
        lineWrap = true
        wrapStyleWord = true
    }
    private val patchList = JList<PatchSuggestion>().apply {
        selectionMode = ListSelectionModel.SINGLE_SELECTION
    }
    private val patchDetailArea = JTextArea(5, 40).apply {
        isEditable = false
        font = Font(Font.MONOSPACED, Font.PLAIN, 10)
    }

    private var lastAnalysisId: String? = null

    init {
        border = JBUI.Borders.empty(8)

        // 패치 목록 렌더러
        patchList.cellRenderer = object : DefaultListCellRenderer() {
            override fun getListCellRendererComponent(list: JList<*>, value: Any?, index: Int, isSelected: Boolean, cellHasFocus: Boolean): java.awt.Component {
                super.getListCellRendererComponent(list, value, index, isSelected, cellHasFocus)
                text = (value as? PatchSuggestion)?.let {
                    "[${(it.confidence * 100).toInt()}%] ${it.filePath} - ${it.description}"
                } ?: ""
                return this
            }
        }
        patchList.addListSelectionListener {
            patchList.selectedValue?.let {
                patchDetailArea.text = it.diffContent
            }
        }

        val btnPanel = JPanel(FlowLayout(FlowLayout.LEFT)).apply {
            add(analyzeBtn.apply { addActionListener { doAnalyze() } })
            add(generatePatchBtn.apply { addActionListener { doGeneratePatch() } })
            add(JButton("Apply Patch").apply {
                addActionListener { doApplyPatch() }
            })
        }

        val splitPane = JSplitPane(JSplitPane.VERTICAL_SPLIT).apply {
            topComponent = JSplitPane(JSplitPane.VERTICAL_SPLIT).apply {
                topComponent = JPanel(BorderLayout()).apply {
                    add(JLabel("로그 입력:"), BorderLayout.NORTH)
                    add(JBScrollPane(logInput), BorderLayout.CENTER)
                }
                bottomComponent = JPanel(BorderLayout()).apply {
                    add(JLabel("분석 결과:"), BorderLayout.NORTH)
                    add(JBScrollPane(resultArea), BorderLayout.CENTER)
                }
                dividerLocation = 200
            }
            bottomComponent = JPanel(BorderLayout()).apply {
                add(JLabel("패치 제안:"), BorderLayout.NORTH)
                add(JSplitPane(JSplitPane.HORIZONTAL_SPLIT).apply {
                    leftComponent = JBScrollPane(patchList)
                    rightComponent = JBScrollPane(patchDetailArea)
                    dividerLocation = 200
                }, BorderLayout.CENTER)
            }
            dividerLocation = 350
        }

        add(btnPanel, BorderLayout.NORTH)
        add(splitPane, BorderLayout.CENTER)
    }

    private fun doAnalyze() {
        val log = logInput.text.trim()
        if (log.isEmpty()) {
            Messages.showWarningDialog(project, "로그를 입력하세요.", "입력 필요")
            return
        }
        val svc = project.getService(CoreEngineService::class.java)
        if (!svc.ensureRunning()) return

        resultArea.text = "분석 중..."
        generatePatchBtn.isEnabled = false

        ApplicationManager.getApplication().executeOnPooledThread {
            runCatching {
                val resp = svc.client.analyzeLog(log, useAi = false)
                lastAnalysisId = resp.analysisId
                val sb = StringBuilder()
                sb.appendLine("전체 심각도: ${resp.overallSeverity.uppercase()}")
                sb.appendLine("탐지된 에러: ${resp.detectedErrors.size}개")
                resp.detectedErrors.forEach { e ->
                    sb.appendLine("\n[${e.severity.uppercase()}] ${e.name} (${e.category})")
                    sb.appendLine("  → ${e.suggestion}")
                    if (e.matchedLines.isNotEmpty()) {
                        sb.appendLine("  매칭된 라인:")
                        e.matchedLines.take(3).forEach { sb.appendLine("    $it") }
                    }
                }
                if (resp.aiSummary.isNotBlank()) {
                    sb.appendLine("\n[AI 분석]\n${resp.aiSummary}")
                }
                SwingUtilities.invokeLater {
                    resultArea.text = sb.toString()
                    resultArea.caretPosition = 0
                    generatePatchBtn.isEnabled = true
                }
            }.onFailure { ex ->
                SwingUtilities.invokeLater { resultArea.text = "분석 실패: ${ex.message}" }
            }
        }
    }

    private fun doGeneratePatch() {
        val aid = lastAnalysisId ?: return
        val svc = project.getService(CoreEngineService::class.java)

        ApplicationManager.getApplication().executeOnPooledThread {
            runCatching {
                val patches = svc.client.generatePatches(aid, useAi = false)
                SwingUtilities.invokeLater {
                    val model = DefaultListModel<PatchSuggestion>()
                    patches.forEach { model.addElement(it) }
                    patchList.model = model
                    if (patches.isEmpty()) resultArea.text += "\n\n패치 제안이 없습니다."
                }
            }.onFailure { ex ->
                SwingUtilities.invokeLater {
                    resultArea.text += "\n패치 생성 실패: ${ex.message}"
                }
            }
        }
    }

    private fun doApplyPatch() {
        val patch = patchList.selectedValue ?: run {
            Messages.showWarningDialog(project, "패치를 선택하세요.", "선택 필요")
            return
        }
        val aid = lastAnalysisId ?: return
        val answer = Messages.showYesNoDialog(
            project,
            "패치를 적용하시겠습니까?\n파일: ${patch.filePath}",
            "패치 적용",
            Messages.getQuestionIcon()
        )
        if (answer != Messages.YES) return

        val svc = project.getService(CoreEngineService::class.java)
        ApplicationManager.getApplication().executeOnPooledThread {
            runCatching {
                // REST API로 패치 적용 요청
                val result = svc.client.let {
                    // analyzeLog / generatePatches 내부 postRaw 활용
                    val body = """{"patch_id":"${patch.id}"}"""
                    // CoreEngineClient의 내부 메서드 접근을 위해 임시 처리
                    Messages.showInfoMessage(
                        project,
                        "패치 적용은 CLI를 사용하세요:\naidevops analyze patch $aid --apply",
                        "안내"
                    )
                }
            }
        }
    }
}
