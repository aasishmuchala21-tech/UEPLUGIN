// NyraTheme.h - Phase 18-F theme-matching colour shim.
// Centralises every NYRA-side colour pull from FAppStyle so a future
// Tier-3 colour audit can swap the source without touching every widget.

#pragma once

#include "CoreMinimal.h"
#include "Styling/AppStyle.h"

struct NYRAEDITOR_API FNyraTheme
{
    static FSlateColor GetAccent()        { return FAppStyle::Get().GetSlateColor("AccentBlue"); }
    static FSlateColor GetForeground()    { return FAppStyle::Get().GetSlateColor("Colors.Foreground"); }
    static FSlateColor GetBackground()    { return FAppStyle::Get().GetSlateColor("Colors.Background"); }
    static FSlateColor GetDanger()        { return FAppStyle::Get().GetSlateColor("AccentRed"); }
    static FSlateColor GetMuted()         { return FAppStyle::Get().GetSlateColor("Colors.Foreground"); }
    static FSlateColor GetPanelHeader()   { return FAppStyle::Get().GetSlateColor("Colors.Header"); }
};
