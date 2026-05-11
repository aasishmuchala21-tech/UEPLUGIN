// Copyright NYRA. All rights reserved.
using UnrealBuildTool;
using System.IO;

public class NyraEditor : ModuleRules
{
    public NyraEditor(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        bUseUnity = false;
        DefaultBuildSettings = BuildSettingsVersion.V5;
        CppStandard = CppStandardVersion.Cpp20;

        PublicIncludePaths.Add(Path.Combine(ModuleDirectory, "Public"));
        PrivateIncludePaths.Add(Path.Combine(ModuleDirectory, "Private"));

        PublicDependencyModuleNames.AddRange(new string[]
        {
            "Core",
            "CoreUObject",
            "Engine",
            "InputCore",
            "Slate",
            "SlateCore",
            "EditorStyle",
            "EditorSubsystem",
            "UnrealEd",
            "ToolMenus",
            "Projects",
            "Json",
            "JsonUtilities",
            "WebSockets",
            "HTTP",
            "DesktopPlatform",
            "ApplicationCore",
            "UMG",
        });

        PrivateDependencyModuleNames.AddRange(new string[]
        {
            "WorkspaceMenuStructure",
            "MainFrame",
            "LevelEditor",
            // Phase 8 PARITY-02 — C++ authoring + Live Coding helper
            "LiveCoding",
            "HotReload",
            // Phase 8 PARITY-03 — Behavior Tree authoring helper
            "AIModule",
            "BehaviorTreeEditor",
            "AssetTools",
            "AssetRegistry",
            // Phase 8 PARITY-05 — Niagara VFX authoring helper
            "Niagara",
            "NiagaraEditor",
            // Phase 8 PARITY-07 — Animation Blueprint authoring helper
            "AnimGraph",
            "AnimGraphRuntime",
            "BlueprintGraph",
            // Plan 09 LDA-01 — procedural blockout via GeometryScript.
            "GeometryScriptingCore",
            "GeometryScriptingEditor",
        });

        // Stage NyraHost + NyraInfer binaries when the plugin is packaged.
        // Folders may be empty in Plan 03; Plans 06 and 08 populate them.
        if (Target.Platform == UnrealTargetPlatform.Win64)
        {
            string PluginBinariesDir = Path.Combine(PluginDirectory, "Binaries", "Win64");

            string NyraHostDir = Path.Combine(PluginBinariesDir, "NyraHost");
            if (Directory.Exists(NyraHostDir))
            {
                foreach (string F in Directory.GetFiles(NyraHostDir, "*", SearchOption.AllDirectories))
                {
                    RuntimeDependencies.Add(F);
                }
            }

            string NyraInferDir = Path.Combine(PluginBinariesDir, "NyraInfer");
            if (Directory.Exists(NyraInferDir))
            {
                foreach (string F in Directory.GetFiles(NyraInferDir, "*", SearchOption.AllDirectories))
                {
                    RuntimeDependencies.Add(F);
                }
            }
        }
    }
}
