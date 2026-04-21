#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleInterface.h"

class NYRAEDITOR_API FNyraEditorModule : public IModuleInterface
{
public:
    virtual void StartupModule() override;
    virtual void ShutdownModule() override;

    static FNyraEditorModule& Get();
    static bool IsAvailable();
};
