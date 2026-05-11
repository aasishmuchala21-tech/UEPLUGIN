// SNyraMaskCanvas.cpp - INPAINT-01 brush-mask painter implementation.
// Plan 09-02. Build status: pending_manual_verification (no UE toolchain).

#include "Panel/SNyraMaskCanvas.h"

#include "Engine/Texture2D.h"
#include "Rendering/SlateRenderer.h"
#include "Framework/Application/SlateApplication.h"
#include "Layout/Geometry.h"
#include "Input/Reply.h"
#include "Input/Events.h"
#include "Misc/Paths.h"
#include "ImageUtils.h"
#include "RenderingThread.h"

namespace
{
    const FLinearColor MaskOverlay(1.0f, 0.0f, 0.0f, 0.5f);

    int32 ClampToRange(int32 V, int32 Lo, int32 Hi)
    {
        return FMath::Clamp(V, Lo, Hi);
    }
}

SNyraMaskCanvas::SNyraMaskCanvas() = default;

SNyraMaskCanvas::~SNyraMaskCanvas()
{
    // FSlateBrush holds a raw UTexture2D*; let GC reclaim. The transient
    // MaskTexture is unrooted -- it's collected with the next GC pass
    // once Slate's reference is dropped.
}

void SNyraMaskCanvas::Construct(const FArguments& InArgs)
{
    SourceImage = InArgs._SourceImage.Get();
    BrushRadius = FMath::Max(1, InArgs._BrushRadius.Get());

    TexW = SourceImage ? static_cast<int32>(SourceImage->GetSizeX()) : 1024;
    TexH = SourceImage ? static_cast<int32>(SourceImage->GetSizeY()) : 1024;

    SourceBrush = MakeShared<FSlateBrush>();
    if (SourceImage)
    {
        SourceBrush->SetResourceObject(SourceImage);
        SourceBrush->ImageSize = FVector2D(TexW, TexH);
    }

    MaskBrush = MakeShared<FSlateBrush>();
    RebuildMaskTexture(TexW, TexH);

    ChildSlot
    [
        SNew(SBorder).BorderImage(FAppStyle::Get().GetBrush("ToolPanel.GroupBorder"))
    ];
}

void SNyraMaskCanvas::RebuildMaskTexture(int32 W, int32 H)
{
    TexW = FMath::Max(1, W);
    TexH = FMath::Max(1, H);
    MaskBuffer.SetNumZeroed(TexW * TexH * 4);
    // Create a transient BGRA texture; PF_B8G8R8A8 is the canonical
    // pixel format for Slate-bound textures (see TextureEditor).
    MaskTexture = UTexture2D::CreateTransient(TexW, TexH, PF_B8G8R8A8);
    if (MaskTexture)
    {
        MaskTexture->SRGB = false;
        MaskTexture->AddToRoot();
        // Push the initial cleared buffer up once so the GPU side has
        // valid contents on first OnPaint.
        FUpdateTextureRegion2D Region(0, 0, 0, 0, TexW, TexH);
        MaskTexture->UpdateTextureRegions(
            0, 1, &Region,
            static_cast<uint32>(TexW * 4),
            static_cast<uint32>(4),
            MaskBuffer.GetData(),
            [](uint8*, const FUpdateTextureRegion2D*) {});
        MaskTexture->UpdateResource();   // ONLY at construction
        MaskBrush->SetResourceObject(MaskTexture);
        MaskBrush->ImageSize = FVector2D(TexW, TexH);
        MaskBrush->TintColor = FSlateColor(MaskOverlay);
    }
}

void SNyraMaskCanvas::Clear()
{
    if (MaskBuffer.Num() == 0 || !MaskTexture) return;
    FMemory::Memzero(MaskBuffer.GetData(), MaskBuffer.Num());
    FUpdateTextureRegion2D FullRegion(0, 0, 0, 0, TexW, TexH);
    MaskTexture->UpdateTextureRegions(
        0, 1, &FullRegion,
        static_cast<uint32>(TexW * 4),
        static_cast<uint32>(4),
        MaskBuffer.GetData(),
        [](uint8*, const FUpdateTextureRegion2D*) {});
    Invalidate(EInvalidateWidget::Paint);   // WR-08
}

void SNyraMaskCanvas::SetBrushRadius(int32 NewRadius)
{
    BrushRadius = FMath::Max(1, NewRadius);
    Invalidate(EInvalidateWidget::Paint);   // WR-08
}

FReply SNyraMaskCanvas::OnMouseButtonDown(const FGeometry& MyGeometry, const FPointerEvent& Evt)
{
    if (Evt.GetEffectingButton() == EKeys::LeftMouseButton)
    {
        bPainting = true;
        PaintAt(MyGeometry, Evt);
        return FReply::Handled().CaptureMouse(SharedThis(this));
    }
    return FReply::Unhandled();
}

FReply SNyraMaskCanvas::OnMouseMove(const FGeometry& MyGeometry, const FPointerEvent& Evt)
{
    if (bPainting)
    {
        PaintAt(MyGeometry, Evt);
        return FReply::Handled();
    }
    return FReply::Unhandled();
}

FReply SNyraMaskCanvas::OnMouseButtonUp(const FGeometry& MyGeometry, const FPointerEvent& Evt)
{
    if (Evt.GetEffectingButton() == EKeys::LeftMouseButton && bPainting)
    {
        bPainting = false;
        return FReply::Handled().ReleaseMouseCapture();
    }
    return FReply::Unhandled();
}

void SNyraMaskCanvas::PaintAt(const FGeometry& MyGeometry, const FPointerEvent& Evt)
{
    if (!MaskTexture) return;

    // Local widget coords (per Phase 0.E research).
    const FVector2D Local = MyGeometry.AbsoluteToLocal(Evt.GetScreenSpacePosition());
    const FVector2D LocalSize = MyGeometry.GetLocalSize();
    if (LocalSize.X <= 0.0f || LocalSize.Y <= 0.0f) return;

    const int32 PxX = static_cast<int32>((Local.X / LocalSize.X) * TexW);
    const int32 PxY = static_cast<int32>((Local.Y / LocalSize.Y) * TexH);

    const int32 R = BrushRadius;
    const int32 X0 = ClampToRange(PxX - R, 0, TexW - 1);
    const int32 X1 = ClampToRange(PxX + R, 0, TexW - 1);
    const int32 Y0 = ClampToRange(PxY - R, 0, TexH - 1);
    const int32 Y1 = ClampToRange(PxY + R, 0, TexH - 1);

    const int32 R2 = R * R;
    for (int32 Y = Y0; Y <= Y1; ++Y)
    {
        for (int32 X = X0; X <= X1; ++X)
        {
            const int32 DX = X - PxX, DY = Y - PxY;
            if (DX*DX + DY*DY > R2) continue;
            const int32 Idx = (Y * TexW + X) * 4;
            // BGRA: the "mask intensity" lives in the R channel; B/G/A
            // copy R so an 8-bit grayscale read of the PNG works.
            MaskBuffer[Idx + 0] = 255;   // B
            MaskBuffer[Idx + 1] = 255;   // G
            MaskBuffer[Idx + 2] = 255;   // R
            MaskBuffer[Idx + 3] = 255;   // A
        }
    }

    // Push only the dirty region.
    const int32 RegionW = X1 - X0 + 1;
    const int32 RegionH = Y1 - Y0 + 1;
    FUpdateTextureRegion2D DirtyRegion(X0, Y0, X0, Y0, RegionW, RegionH);
    MaskTexture->UpdateTextureRegions(
        0, 1, &DirtyRegion,
        static_cast<uint32>(TexW * 4),
        static_cast<uint32>(4),
        MaskBuffer.GetData(),
        [](uint8*, const FUpdateTextureRegion2D*) {});

    Invalidate(EInvalidateWidget::Paint);   // WR-08
}

int32 SNyraMaskCanvas::OnPaint(
    const FPaintArgs& Args,
    const FGeometry& AllottedGeometry,
    const FSlateRect& MyCullingRect,
    FSlateWindowElementList& OutDrawElements,
    int32 LayerId,
    const FWidgetStyle& InWidgetStyle,
    bool bParentEnabled) const
{
    LayerId = SCompoundWidget::OnPaint(
        Args, AllottedGeometry, MyCullingRect,
        OutDrawElements, LayerId, InWidgetStyle, bParentEnabled);

    if (SourceBrush.IsValid() && SourceImage)
    {
        FSlateDrawElement::MakeBox(
            OutDrawElements, LayerId,
            AllottedGeometry.ToPaintGeometry(),
            SourceBrush.Get(),
            ESlateDrawEffect::None,
            FLinearColor::White);
    }
    if (MaskBrush.IsValid() && MaskTexture)
    {
        FSlateDrawElement::MakeBox(
            OutDrawElements, LayerId + 1,
            AllottedGeometry.ToPaintGeometry(),
            MaskBrush.Get(),
            ESlateDrawEffect::None,
            MaskOverlay);
    }
    return LayerId + 2;
}

FVector2D SNyraMaskCanvas::ComputeDesiredSize(float) const
{
    return FVector2D(FMath::Min(TexW, 1024), FMath::Min(TexH, 1024));
}

TArray<uint8> SNyraMaskCanvas::ExportMaskPng() const
{
    // Re-pack BGRA -> FColor for FImageUtils.
    TArray<FColor> Pixels;
    Pixels.SetNumUninitialized(TexW * TexH);
    for (int32 i = 0; i < TexW * TexH; ++i)
    {
        const int32 j = i * 4;
        Pixels[i] = FColor(
            MaskBuffer.IsValidIndex(j + 2) ? MaskBuffer[j + 2] : 0,  // R
            MaskBuffer.IsValidIndex(j + 1) ? MaskBuffer[j + 1] : 0,  // G
            MaskBuffer.IsValidIndex(j + 0) ? MaskBuffer[j + 0] : 0,  // B
            MaskBuffer.IsValidIndex(j + 3) ? MaskBuffer[j + 3] : 0); // A
    }
    TArray<uint8> Png;
    FImageUtils::ThumbnailCompressImageArray(TexW, TexH, Pixels, Png);
    return Png;
}
