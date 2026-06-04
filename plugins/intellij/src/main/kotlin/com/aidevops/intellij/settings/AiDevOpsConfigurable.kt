package com.aidevops.intellij.settings

import com.intellij.openapi.options.Configurable
import com.intellij.ui.components.JBCheckBox
import com.intellij.ui.components.JBLabel
import com.intellij.ui.components.JBTextField
import com.intellij.util.ui.FormBuilder
import javax.swing.JComponent
import javax.swing.JPanel

class AiDevOpsConfigurable : Configurable {

    private val portField = JBTextField(6)
    private val autoStartCheckBox = JBCheckBox("Core Engine 자동 시작")
    private val enginePathField = JBTextField(40)
    private val cicdPlatformField = JBTextField(20)

    private var panel: JPanel? = null

    override fun getDisplayName(): String = "AI DevOps"

    override fun createComponent(): JComponent {
        val settings = AiDevOpsSettings.instance
        portField.text = settings.coreEnginePort.toString()
        autoStartCheckBox.isSelected = settings.autoStartEngine
        enginePathField.text = settings.coreEnginePath
        cicdPlatformField.text = settings.defaultCicdPlatform

        panel = FormBuilder.createFormBuilder()
            .addLabeledComponent(JBLabel("Core Engine 포트:"), portField)
            .addComponent(autoStartCheckBox)
            .addLabeledComponent(JBLabel("Core Engine 경로 (비워두면 PATH 자동 탐색):"), enginePathField)
            .addLabeledComponent(JBLabel("기본 CI/CD 플랫폼:"), cicdPlatformField)
            .addComponentFillVertically(JPanel(), 0)
            .panel

        return panel!!
    }

    override fun isModified(): Boolean {
        val s = AiDevOpsSettings.instance
        return portField.text.toIntOrNull() != s.coreEnginePort
                || autoStartCheckBox.isSelected != s.autoStartEngine
                || enginePathField.text != s.coreEnginePath
                || cicdPlatformField.text != s.defaultCicdPlatform
    }

    override fun apply() {
        val s = AiDevOpsSettings.instance
        portField.text.toIntOrNull()?.let { s.coreEnginePort = it }
        s.autoStartEngine = autoStartCheckBox.isSelected
        s.coreEnginePath = enginePathField.text
        s.defaultCicdPlatform = cicdPlatformField.text
    }

    override fun reset() {
        val s = AiDevOpsSettings.instance
        portField.text = s.coreEnginePort.toString()
        autoStartCheckBox.isSelected = s.autoStartEngine
        enginePathField.text = s.coreEnginePath
        cicdPlatformField.text = s.defaultCicdPlatform
    }
}
