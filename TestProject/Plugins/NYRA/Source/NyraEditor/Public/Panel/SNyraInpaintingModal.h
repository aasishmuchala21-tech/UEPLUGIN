// SNyraInpaintingModal.h - INPAINT-01 in-painting modal shell.
// Plan 09-02. Build status: pending_manual_verification (no UE toolchain).
//
// Layout (per PLAN_aura_killers_1wk.md §2.3):
//   SHorizontalBox
//     ├── [70%] SNyraMaskCanvas
//     └── [30%] SVerticalBox
//          ├── SButton "Clear mask"
//          ├── STextBlock "Brush size"
//          ├── SSlider [4..64]
//          ├── SBorder "Reference panel" (deferred wiring -- ControlNet
//          │            and IPAdapter routing land in v1.1)
//          ├── SEditableTextBox "Prompt"
//          ├── SEditableTextBox "Negative prompt"
//          └── SButton "Generate" PRIMARY
//
// Submission flow: on "Generate", the modal exports the mask PNG via
// SNyraMaskCanvas::ExportMaskPng(), reads the source UTexture2D's bytes,
// base64-encodes both, and emits a JSON-RPC request `inpaint/submit`
// over the existing supervisor WS. The result image_path is imported
// back into Content/NYRA/Inpaint/ via AssetTools.

#pragma once

#include "CoreMinimal.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SCompoundWidget.h"

class UTexture2D;
class SNyraMaskCanvas;
class SEditableTextBox;
class SSlider;

DECLARE_DELEGATE_OneParam(FOnNyraInpaintComplete, const FString& /*ImportedAssetPath*/);

class NYRAEDITOR_API SNyraInpaintingModal : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SNyraInpaintingModal)
        : _SourceImage(nullptr) {}
        SLATE_ATTRIBUTE(UTexture2D*, SourceImage)
        SLATE_EVENT(FOnNyraInpaintComplete, OnInpaintComplete)
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);

private:
    FReply HandleClear();
    FReply HandleGenerate();
    void OnBrushSliderChanged(float NewValue);

    UTexture2D* SourceImage = nullptr;
    TSharedPtr<SNyraMaskCanvas> MaskCanvas;
    TSharedPtr<SEditableTextBox> PromptBox;
    TSharedPtr<SEditableTextBox> NegativePromptBox;
    TSharedPtr<SSlider> BrushSlider;
    FOnNyraInpaintComplete OnComplete;
};
