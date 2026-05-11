// SNyraInpaintingModal.cpp - INPAINT-01 in-painting modal shell.
// Plan 09-02. Build status: pending_manual_verification (no UE toolchain).

#include "Panel/SNyraInpaintingModal.h"
#include "Panel/SNyraMaskCanvas.h"

#include "Process/FNyraSupervisor.h"
#include "WS/FNyraJsonRpc.h"

#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Input/SSlider.h"
#include "Widgets/SBoxPanel.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/Base64.h"
#include "Dom/JsonObject.h"

extern TUniquePtr<class FNyraSupervisor> GNyraSupervisor;

namespace
{
    const FLinearColor Dominant(0.02f, 0.02f, 0.03f, 1.0f);
    const FLinearColor Accent(0.776f, 0.749f, 1.0f, 1.0f);
    const FLinearColor TextDim(0.6f, 0.6f, 0.65f, 1.0f);

    /** Read raw BGRA pixels from a UTexture2D and PNG-encode them.
     *  v0 limitation: only platform-data Mip0 is supported. If the
     *  texture is virtual or compressed, returns an empty array and
     *  the caller surfaces a "unsupported source image" error to the
     *  user. */
    TArray<uint8> EncodeSourceAsPng(UTexture2D* Tex)
    {
        if (!Tex || !Tex->GetPlatformData() || Tex->GetPlatformData()->Mips.Num() == 0)
        {
            return {};
        }
        const FTexture2DMipMap& Mip = Tex->GetPlatformData()->Mips[0];
        const int32 W = Mip.SizeX;
        const int32 H = Mip.SizeY;
        FByteBulkData& Bulk = const_cast<FByteBulkData&>(Mip.BulkData);
        const void* Data = Bulk.LockReadOnly();
        TArray<FColor> Pixels;
        Pixels.SetNumUninitialized(W * H);
        if (Data)
        {
            FMemory::Memcpy(Pixels.GetData(), Data, W * H * sizeof(FColor));
        }
        Bulk.Unlock();
        TArray<uint8> Png;
        FImageUtils::ThumbnailCompressImageArray(W, H, Pixels, Png);
        return Png;
    }
}

void SNyraInpaintingModal::Construct(const FArguments& InArgs)
{
    SourceImage = InArgs._SourceImage.Get();
    OnComplete = InArgs._OnInpaintComplete;

    ChildSlot
    [
        SNew(SBorder)
        .BorderImage(FAppStyle::Get().GetBrush("ToolPanel.GroupBorder"))
        .BorderBackgroundColor(Dominant)
        [
            SNew(SHorizontalBox)
            // Canvas (70%)
            + SHorizontalBox::Slot().FillWidth(0.7f).Padding(4)
            [
                SAssignNew(MaskCanvas, SNyraMaskCanvas)
                .SourceImage(SourceImage)
                .BrushRadius(16)
            ]
            // Sidebar (30%)
            + SHorizontalBox::Slot().FillWidth(0.3f).Padding(4)
            [
                SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 6)
                [
                    SNew(SButton)
                    .Text(FText::FromString(TEXT("Clear mask")))
                    .OnClicked(this, &SNyraInpaintingModal::HandleClear)
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 6, 0, 2)
                [
                    SNew(STextBlock)
                    .ColorAndOpacity(TextDim)
                    .Text(FText::FromString(TEXT("Brush size")))
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
                [
                    SAssignNew(BrushSlider, SSlider)
                    .MinValue(4.0f).MaxValue(64.0f).Value(16.0f)
                    .OnValueChanged(this, &SNyraInpaintingModal::OnBrushSliderChanged)
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 6, 0, 2)
                [
                    SNew(STextBlock)
                    .ColorAndOpacity(TextDim)
                    .Text(FText::FromString(TEXT("Reference panel (v1.1)")))
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
                [
                    SNew(SBorder)
                    .BorderImage(FAppStyle::Get().GetBrush("ToolPanel.GroupBorder"))
                    .Padding(8)
                    [
                        SNew(STextBlock)
                        .ColorAndOpacity(TextDim)
                        .Text(FText::FromString(TEXT(
                            "ControlNet / IPAdapter wiring lands in v1.1.\n"
                            "v0 ships SDXL inpaint without reference guidance.")))
                    ]
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 6, 0, 2)
                [
                    SNew(STextBlock)
                    .ColorAndOpacity(TextDim)
                    .Text(FText::FromString(TEXT("Prompt")))
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 6)
                [
                    SAssignNew(PromptBox, SEditableTextBox)
                    .HintText(FText::FromString(TEXT("e.g. \"sunglasses\"")))
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 6, 0, 2)
                [
                    SNew(STextBlock)
                    .ColorAndOpacity(TextDim)
                    .Text(FText::FromString(TEXT("Negative prompt")))
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 12)
                [
                    SAssignNew(NegativePromptBox, SEditableTextBox)
                    .HintText(FText::FromString(TEXT("e.g. \"blurry, low quality\"")))
                ]
                + SVerticalBox::Slot().AutoHeight()
                [
                    SNew(SButton)
                    .ButtonColorAndOpacity(Accent)
                    .Text(FText::FromString(TEXT("Generate")))
                    .OnClicked(this, &SNyraInpaintingModal::HandleGenerate)
                ]
            ]
        ]
    ];
}

FReply SNyraInpaintingModal::HandleClear()
{
    if (MaskCanvas.IsValid()) MaskCanvas->Clear();
    return FReply::Handled();
}

void SNyraInpaintingModal::OnBrushSliderChanged(float NewValue)
{
    if (MaskCanvas.IsValid())
    {
        MaskCanvas->SetBrushRadius(static_cast<int32>(NewValue));
    }
}

FReply SNyraInpaintingModal::HandleGenerate()
{
    if (!GNyraSupervisor.IsValid() || !MaskCanvas.IsValid() || !SourceImage)
    {
        return FReply::Handled();
    }
    const TArray<uint8> SourcePng = EncodeSourceAsPng(SourceImage);
    const TArray<uint8> MaskPng = MaskCanvas->ExportMaskPng();
    if (SourcePng.Num() == 0 || MaskPng.Num() == 0)
    {
        return FReply::Handled();
    }

    const FString SourceB64 = FBase64::Encode(SourcePng);
    const FString MaskB64 = FBase64::Encode(MaskPng);

    TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
    Params->SetStringField(TEXT("source_image_b64"), SourceB64);
    Params->SetStringField(TEXT("mask_b64"), MaskB64);
    Params->SetStringField(
        TEXT("prompt"),
        PromptBox.IsValid() ? PromptBox->GetText().ToString() : FString());
    Params->SetStringField(
        TEXT("negative_prompt"),
        NegativePromptBox.IsValid() ? NegativePromptBox->GetText().ToString() : FString());
    Params->SetNumberField(TEXT("denoise"), 0.85);
    Params->SetNumberField(TEXT("steps"), 30);
    Params->SetNumberField(TEXT("cfg"), 7.0);
    Params->SetNumberField(TEXT("seed"), -1);

    GNyraSupervisor->SendRequest(TEXT("inpaint/submit"), Params);
    return FReply::Handled();
}
