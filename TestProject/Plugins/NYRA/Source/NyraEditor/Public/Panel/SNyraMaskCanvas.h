// SNyraMaskCanvas.h - INPAINT-01 brush-mask painter for the in-painting modal.
// Plan 09-02. Build status: pending_manual_verification (no UE toolchain).
//
// Implementation contract (per PLAN_aura_killers_1wk.md §2.2):
//   - Owns a UTexture2D* SourceImage (set via SLATE_ATTRIBUTE) plus a
//     transient UTexture2D* MaskTexture sized to the source.
//   - On mouse down/move with capture, splats a circle of BrushRadius
//     into a CPU-side BGRA backbuffer and pushes only the dirty
//     FUpdateTextureRegion2D to the GPU via UpdateTextureRegions.
//   - OnPaint draws the source image at LayerId and a 50% red overlay
//     of the mask at LayerId+1.
//   - ExportMaskPng() returns a compressed PNG buffer the modal hands
//     to the WS request.
//
// WR-08: every state change (brush stroke, BrushRadius set, Clear)
// calls Invalidate(EInvalidateWidget::Paint) explicitly so the mask
// overlay updates without waiting for the next pulse.

#pragma once

#include "CoreMinimal.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SCompoundWidget.h"
#include "Styling/SlateBrush.h"

class UTexture2D;
struct FUpdateTextureRegion2D;

class NYRAEDITOR_API SNyraMaskCanvas : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SNyraMaskCanvas)
        : _SourceImage(nullptr), _BrushRadius(16) {}
        SLATE_ATTRIBUTE(UTexture2D*, SourceImage)
        SLATE_ATTRIBUTE(int32, BrushRadius)
    SLATE_END_ARGS()

    SNyraMaskCanvas();
    virtual ~SNyraMaskCanvas();

    void Construct(const FArguments& InArgs);

    /** Reset the mask to fully-unmasked (alpha=0). */
    void Clear();

    /** Update brush radius in widget pixels. */
    void SetBrushRadius(int32 NewRadius);

    /** Encode the mask as an 8-bit grayscale PNG (red channel carries
     *  the mask intensity). */
    TArray<uint8> ExportMaskPng() const;

    // SWidget overrides
    virtual int32 OnPaint(
        const FPaintArgs& Args,
        const FGeometry& AllottedGeometry,
        const FSlateRect& MyCullingRect,
        FSlateWindowElementList& OutDrawElements,
        int32 LayerId,
        const FWidgetStyle& InWidgetStyle,
        bool bParentEnabled) const override;
    virtual FReply OnMouseButtonDown(
        const FGeometry& MyGeometry,
        const FPointerEvent& Evt) override;
    virtual FReply OnMouseMove(
        const FGeometry& MyGeometry,
        const FPointerEvent& Evt) override;
    virtual FReply OnMouseButtonUp(
        const FGeometry& MyGeometry,
        const FPointerEvent& Evt) override;
    virtual FVector2D ComputeDesiredSize(float) const override;

private:
    void RebuildMaskTexture(int32 W, int32 H);
    void PaintAt(const FGeometry& MyGeometry, const FPointerEvent& Evt);

    UTexture2D* SourceImage = nullptr;
    UTexture2D* MaskTexture = nullptr;

    int32 TexW = 0;
    int32 TexH = 0;
    int32 BrushRadius = 16;
    bool bPainting = false;

    /** BGRA backbuffer; MaskTexture is updated from this on every stroke. */
    TArray<uint8> MaskBuffer;

    /** Slate brushes carrying SourceImage and MaskTexture as resource
     *  objects so MakeBox can render them. */
    TSharedPtr<FSlateBrush> SourceBrush;
    TSharedPtr<FSlateBrush> MaskBrush;
};
