package com.aidevops.intellij.settings

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.PersistentStateComponent
import com.intellij.openapi.components.State
import com.intellij.openapi.components.Storage

@State(
    name = "AiDevOpsSettings",
    storages = [Storage("aidevops.xml")]
)
class AiDevOpsSettings : PersistentStateComponent<AiDevOpsSettings.State> {

    data class State(
        var coreEnginePort: Int = 8765,
        var autoStartEngine: Boolean = true,
        var coreEnginePath: String = "",   // 빈 문자열이면 PATH에서 자동 탐색
        var defaultCicdPlatform: String = "github_actions",
    )

    private var myState = State()

    override fun getState(): State = myState
    override fun loadState(state: State) { myState = state }

    companion object {
        val instance: AiDevOpsSettings
            get() = ApplicationManager.getApplication()
                .getService(AiDevOpsSettings::class.java)
    }

    var coreEnginePort: Int
        get() = myState.coreEnginePort
        set(v) { myState = myState.copy(coreEnginePort = v) }

    var autoStartEngine: Boolean
        get() = myState.autoStartEngine
        set(v) { myState = myState.copy(autoStartEngine = v) }

    var coreEnginePath: String
        get() = myState.coreEnginePath
        set(v) { myState = myState.copy(coreEnginePath = v) }

    var defaultCicdPlatform: String
        get() = myState.defaultCicdPlatform
        set(v) { myState = myState.copy(defaultCicdPlatform = v) }
}
