// SNyraKeyboardShortcuts.h - Phase 18-F keyboard shortcuts helper.
// Build status: pending_manual_verification.
//
// Bind into the composer's OnKeyDown:
//   * Ctrl+Enter  → send
//   * Esc         → cancel in-flight
//   * Up arrow    → previous prompt in history
//   * Down arrow  → next prompt in history

#pragma once

#include "CoreMinimal.h"
#include "Input/Events.h"
#include "Input/Reply.h"

DECLARE_DELEGATE(FOnNyraShortcutSend);
DECLARE_DELEGATE(FOnNyraShortcutCancel);
DECLARE_DELEGATE(FOnNyraShortcutHistoryPrev);
DECLARE_DELEGATE(FOnNyraShortcutHistoryNext);

struct NYRAEDITOR_API FNyraKeyboardShortcuts
{
    FOnNyraShortcutSend         OnSend;
    FOnNyraShortcutCancel       OnCancel;
    FOnNyraShortcutHistoryPrev  OnPrev;
    FOnNyraShortcutHistoryNext  OnNext;

    /** Dispatch the key event. Returns FReply::Handled() iff it matched. */
    FReply Dispatch(const FKeyEvent& Evt) const
    {
        const FKey Key = Evt.GetKey();
        const FModifierKeysState Mods = Evt.GetModifierKeys();

        if (Key == EKeys::Enter && Mods.IsControlDown())
        {
            OnSend.ExecuteIfBound();
            return FReply::Handled();
        }
        if (Key == EKeys::Escape)
        {
            OnCancel.ExecuteIfBound();
            return FReply::Handled();
        }
        if (Key == EKeys::Up && !Mods.AnyModifiersDown())
        {
            OnPrev.ExecuteIfBound();
            return FReply::Handled();
        }
        if (Key == EKeys::Down && !Mods.AnyModifiersDown())
        {
            OnNext.ExecuteIfBound();
            return FReply::Handled();
        }
        return FReply::Unhandled();
    }
};
