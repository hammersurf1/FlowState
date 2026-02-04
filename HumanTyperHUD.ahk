#Requires AutoHotkey v2.0
#SingleInstance Force

; -------------------------------------------------------------------------
; CORE SETTINGS & INITIALIZATION
; -------------------------------------------------------------------------
Global IniFile := A_ScriptDir "\settings.ini"

; --- TUNED FOR REALISM V3 (FASTER & LESS UNIFORM) ---
Global DefaultMeanDelay  := 40  ; Reduced from 60 to compensate for Key Hold Time
Global DefaultVariance   := 35  ; Increased from 25 to add more rhythm imperfection
Global DefaultTypoChance := 4
Global DefaultTypoDelay  := 150

; Cognitive Defaults
Global DefaultSentencePause  := 1200
Global DefaultParagraphPause := 2000
Global DefaultBrainstormFreq := 60
Global DefaultEmojiPause     := 1800 

; Runtime Vars
Global UserMeanDelay   := DefaultMeanDelay
Global UserVariance    := DefaultVariance
Global TypoChance      := DefaultTypoChance
Global TypoDelay       := DefaultTypoDelay
Global SentencePause   := DefaultSentencePause
Global ParagraphPause  := DefaultParagraphPause
Global BrainstormFreq  := DefaultBrainstormFreq
Global EmojiPause      := DefaultEmojiPause
Global CurrentMomentum := 0 

; Pause State Variable
Global IsPaused := false

; Layout Maps
Global LayoutMaps := Map()
InitializeLayouts()

; HUD Globals
Global CurrentSettingIndex := 1
Global SettingsList := ["UserMeanDelay", "UserVariance", "TypoChance", "TypoDelay"]
Global SettingNames := ["Typing Speed (Lower is Faster)", "Variance (Consistency)", "Typo Chance (%)", "Typo Correction Speed"]
Global DefaultsMap := Map("UserMeanDelay", DefaultMeanDelay, "UserVariance", DefaultVariance, "TypoChance", DefaultTypoChance, "TypoDelay", DefaultTypoDelay)

; Load INI
if !FileExist(IniFile)
    SaveSettings()
else
    LoadSettings()

; -------------------------------------------------------------------------
; HUD & SETTINGS HOTKEYS (Alt + Arrows)
; -------------------------------------------------------------------------
!Up::
!Down::
{
    Global CurrentSettingIndex
    if (A_ThisHotkey = "!Up")
        CurrentSettingIndex++
    else
        CurrentSettingIndex--
    
    if (CurrentSettingIndex > SettingsList.Length)
        CurrentSettingIndex := 1
    if (CurrentSettingIndex < 1)
        CurrentSettingIndex := SettingsList.Length
    ShowHUD()
}

!Right::
!Left::
{
    Global UserMeanDelay, UserVariance, TypoChance, TypoDelay, CurrentSettingIndex
    CurrentVar := SettingsList[CurrentSettingIndex]
    CurrentVal := %CurrentVar%
    Step := (CurrentVar = "TypoChance") ? 1 : (CurrentVar = "TypoDelay") ? 25 : 5

    if (A_ThisHotkey = "!Right")
        %CurrentVar% := CurrentVal + Step
    else
        %CurrentVar% := CurrentVal - Step
    
    if (%CurrentVar% < 0)
        %CurrentVar% := 0
        
    SaveSettings()
    ShowHUD()
}

ShowHUD() {
    Global CurrentSettingIndex, SettingsList, SettingNames, DefaultsMap
    CurrentVar := SettingsList[CurrentSettingIndex]
    CurrentVal := %CurrentVar%
    FriendlyName := SettingNames[CurrentSettingIndex]
    DefaultVal := DefaultsMap[CurrentVar]
    ToolTip("⚙️ SETTING: " FriendlyName "`nVALUE: " CurrentVal "  (Default: " DefaultVal ")`n(Use Alt+Left/Right to adjust)")
    SetTimer () => ToolTip(), -3000
}

SaveSettings() {
    IniWrite(UserMeanDelay, IniFile, "Settings", "UserMeanDelay")
    IniWrite(UserVariance,  IniFile, "Settings", "UserVariance")
    IniWrite(TypoChance,    IniFile, "Settings", "TypoChance")
    IniWrite(TypoDelay,     IniFile, "Settings", "TypoDelay")
    IniWrite(SentencePause, IniFile, "Advanced", "SentencePauseMs")
    IniWrite(ParagraphPause,IniFile, "Advanced", "ParagraphPauseMs")
    IniWrite(BrainstormFreq,IniFile, "Advanced", "BrainstormFrequency")
    IniWrite(EmojiPause,    IniFile, "Advanced", "EmojiPauseMs")
}

LoadSettings() {
    Global UserMeanDelay  := IniRead(IniFile, "Settings", "UserMeanDelay", DefaultMeanDelay)
    Global UserVariance   := IniRead(IniFile, "Settings", "UserVariance", DefaultVariance)
    Global TypoChance     := IniRead(IniFile, "Settings", "TypoChance", DefaultTypoChance)
    Global TypoDelay      := IniRead(IniFile, "Settings", "TypoDelay", DefaultTypoDelay)
    Global SentencePause  := IniRead(IniFile, "Advanced", "SentencePauseMs", DefaultSentencePause)
    Global ParagraphPause := IniRead(IniFile, "Advanced", "ParagraphPauseMs", DefaultParagraphPause)
    Global BrainstormFreq := IniRead(IniFile, "Advanced", "BrainstormFrequency", DefaultBrainstormFreq)
    Global EmojiPause     := IniRead(IniFile, "Advanced", "EmojiPauseMs", DefaultEmojiPause)
}

; -------------------------------------------------------------------------
; PAUSE TOGGLE (F1)
; -------------------------------------------------------------------------
F1::
{
    Global IsPaused := !IsPaused
}

; -------------------------------------------------------------------------
; PRODUCTION TYPING ENGINE: Ctrl + Alt + V
; -------------------------------------------------------------------------
^!v::
{
    Global IsPaused
    
    if !A_Clipboard
        return

    KeyWait "Ctrl"
    KeyWait "Shift"
    KeyWait "Alt"

    TargetWin := WinExist("A")
    ActiveLayout := DetectKeyboardLayout(TargetWin)
    NeighborMap := GetLayoutMap(ActiveLayout)

    TextToType := StrReplace(A_Clipboard, "`r`n", "`n")
    TotalLen := StrLen(TextToType)

    if (TotalLen > 5000) {
        if (MsgBox("Type " TotalLen " chars?", "Large Paste", "YesNo IconExclamation") = "No")
            return
    }

    ; --- SETUP KEYBOARD BLOCKER ---
    Blocker := InputHook("L0")
    Blocker.MinSendLevel := 2 
    Blocker.KeyOpt("{All}", "S")        ; Suppress (Block) all keys it sees
    Blocker.KeyOpt("{F1}{Esc}", "-S")   ; Explicitly allow F1 (Pause) and Esc (Cancel)
    Blocker.Start()

    CurrentMomentum := 0
    IsPaused := false
    i := 1
    
    While (i <= TotalLen)
    {
        ; --- PAUSE LOGIC ---
        if (IsPaused) {
            Blocker.Stop() ; Re-enable keyboard so user can type/fix things
            ToolTip("⏸️ PAUSED (Press F1 to Resume)")
            
            While (IsPaused) {
                if GetKeyState("Esc", "P") { ; Allow quitting while paused
                    ToolTip("🔴 CANCELLED")
                    SetTimer () => ToolTip(), -2000
                    return
                }
                Sleep 100
            }
            
            ; Resuming
            ToolTip("▶️ RESUMING...")
            SetTimer () => ToolTip(), -1000
            WinActivate(TargetWin) ; Ensure we are back in the window
            Blocker.Start() ; Re-block keyboard
        }

        ; --- CANCEL LOGIC ---
        if GetKeyState("Esc", "P") {
            Blocker.Stop()
            ToolTip("🔴 CANCELLED")
            SetTimer () => ToolTip(), -2000
            return
        }

        if !WinActive(TargetWin)
            WinActivate(TargetWin)

        Char := SubStr(TextToType, i, 1)
        CharCode := Ord(Char)
        
        ; -----------------------------------------------------------------------
        ; FEATURE C: DELAYED TYPO REALIZATION
        ; -----------------------------------------------------------------------
        if (CharCode < 128 && Char != " " && Char != "`n" && Random(1, 100) <= TypoChance)
        {
            Neighbor := GetNeighbor(Char, NeighborMap)
            
            ; Only proceed if we found a valid neighbor key to "fat finger"
            if (Neighbor != "") {
                ; Determine how many characters we type before "noticing" the error (0 to 3)
                RealizationDelay := Random(0, 3) 
                
                ; Don't overrun the text length
                if (i + RealizationDelay >= TotalLen)
                    RealizationDelay := 0

                ; 1. Type the WRONG character first
                HumanKeystroke(Neighbor) 
                
                ; 2. Type the "Buffer" characters (we haven't realized the error yet)
                Loop RealizationDelay {
                    BufferChar := SubStr(TextToType, i + A_Index, 1)
                    HumanKeystroke(BufferChar)
                    ; Standard spacing between these oblivious characters
                    Sleep GaussianRandom(UserMeanDelay, UserVariance)
                }

                ; 3. THE "OH CRAP" MOMENT (Pause)
                Sleep Random(TypoDelay * 2, TypoDelay * 4) 

                ; 4. Rapidly Backspace (Faster than normal typing)
                Loop (RealizationDelay + 1) {
                    SendEvent "{Backspace}"
                    Sleep Random(30, 60) ; Fast distinct backspaces
                }
                
                Sleep Random(100, 200) ; Brief reset pause
                CurrentMomentum := 0   ; Momentum destroyed by error
                
                ; We do NOT increment 'i' here. We loop back and try the original char again.
                continue 
            }
        }

        ; --- A. EMOJI & UNICODE (WITH PAUSE) ---
        if (CharCode >= 0xD800 && CharCode <= 0xDBFF) {
            Sleep Random(EmojiPause, EmojiPause + 500)
            FullEmoji := SubStr(TextToType, i, 2)
            SurgicalPaste(FullEmoji) 
            Sleep UserMeanDelay
            CurrentMomentum := 0 
            i += 2 
            continue
        }

        NextChar := (i < TotalLen) ? SubStr(TextToType, i+1, 1) : ""

        ; --- B. COGNITIVE PAUSES ---
        if (Char = "." || Char = "?" || Char = "!") && (NextChar = " " || NextChar = "`n") {
            HumanKeystroke(Char)
            Sleep Random(SentencePause, SentencePause + 400) 
            CurrentMomentum := 0 
            i++
            continue
        }

        if (Char = "," || Char = ";") {
            HumanKeystroke(Char)
            Sleep Random(300, 600) 
            CurrentMomentum := Max(0, CurrentMomentum - 5)
            i++
            continue
        }

        if (Char = " " && Random(1, BrainstormFreq) = 1) {
            Sleep Random(1500, 4000) 
            CurrentMomentum := 0 
        }

        ; --- D. EXECUTION ---
        if (Char = "`n") {
            SendEvent "+{Enter}"
            Sleep Random(ParagraphPause, ParagraphPause + 1000) 
            CurrentMomentum := 0
        } else if (Char = "`t") {
            SendEvent "{Tab}"
            Sleep Random(50, 100)
        } else {
            HumanKeystroke(Char)
            if (CurrentMomentum < 15)
                CurrentMomentum += 0.5
        }

        ; --- E. TIMING ---
        CalcMean := UserMeanDelay - CurrentMomentum
        if (InStr("th,he,in,er,an,re,on,at,en,nd,ti,es,or,te,of,ed,is,it,al,ar,st,to,nt", StrLower(Char . NextChar)))
            CalcMean -= 10

        FinalDelay := GaussianRandom(CalcMean, UserVariance)
        if (FinalDelay < 10)
            FinalDelay := 10
        if (FinalDelay > 250)
            FinalDelay := 250

        Sleep FinalDelay
        i++ 
    }

    ; --- CLEANUP ---
    Blocker.Stop() ; Important: Unblock keyboard when done
    ToolTip("✅ DONE")
    SetTimer () => ToolTip(), -2000
}

; -------------------------------------------------------------------------
; HELPERS
; -------------------------------------------------------------------------

; FEATURE A: REALISTIC KEY DWELL TIME (TUNED FOR LIGHT TOUCH)
HumanKeystroke(Char) {
    ; 1. Calculate realistic "Hold Time" (Dwell)
    ; V3 UPDATE: Lowered to 10-40ms (Light, fast touch) vs previous 40-90ms (Heavy/Slow)
    DwellTime := Random(10, 40)
    
    ; 2. Apply this to the keystroke
    ; SetKeyDelay: Delay, PressDuration
    SetKeyDelay 0, DwellTime
    
    ; 3. Handle Special Shift Logic (Shift Overlap)
    if IsUpper(Char) && Char != " " {
        ; Sometimes humans hold Shift a bit too long
        if (Random(1, 10) > 7)
            SetKeyDelay 0, DwellTime + Random(20, 50)
    }

    if (Char = "{")
        SendEvent "{{}"
    else if (Char = "}")
        SendEvent "{}}"
    else if (Char = "+")
        SendEvent "{+}"
    else if (Char = "^")
        SendEvent "{^}"
    else if (Char = "%")
        SendEvent "{%}"
    else if (Char = "!")
        SendEvent "{!}"
    else if (Char = "#")
        SendEvent "{#}"
    else
        SendEvent "{Raw}" Char
        
    ; Reset to default safe values
    SetKeyDelay 10, 10
}

SurgicalPaste(Content) {
    SavedClip := ClipboardAll()
    A_Clipboard := Content
    SendEvent "^v"
    Sleep 50
    A_Clipboard := SavedClip
}

GaussianRandom(Mean, StdDev) {
    RandSum := Random(0.0, 1.0) + Random(0.0, 1.0) + Random(0.0, 1.0)
    StandardNormal := (RandSum - 1.5) / 0.5 
    Return Floor(Mean + (StandardNormal * StdDev))
}

DetectKeyboardLayout(WinID) {
    Try {
        ThreadID := DllCall("GetWindowThreadProcessId", "Ptr", WinID, "Ptr", 0)
        KBID := DllCall("GetKeyboardLayout", "UInt", ThreadID, "Ptr")
        LangID := KBID & 0xFFFF
        if (LangID = 0x0407)
            return "QWERTZ"
        if (LangID = 0x040C)
            return "AZERTY"
        return "QWERTY"
    }
    return "QWERTY"
}

GetLayoutMap(LayoutName) {
    if LayoutMaps.Has(LayoutName)
        return LayoutMaps[LayoutName]
    return LayoutMaps["QWERTY"]
}

GetNeighbor(key, MapToUse) {
    key := StrLower(key)
    if MapToUse.Has(key) {
        choices := MapToUse[key]
        return SubStr(choices, Random(1, StrLen(choices)), 1)
    }
    return "" 
}

InitializeLayouts() {
    ; QWERTY (Numbers isolated from letters)
    LayoutMaps["QWERTY"] := Map(
        "q","wa", "w","qase", "e","wsdr", "r","edft", "t","rfgy", "y","tghu", "u","yhji", "i","ujko", "o","iklp", "p","ol",
        "a","qwsz", "s","qweadzx", "d","wersfcx", "f","ertdgvc", "g","rtyfhvb", "h","tyugjbn", "j","yuihkmn", "k","uiojlm,", "l","iopk;",
        "z","asx", "x","zsdc", "c","xdfv", "v","cfgb", "b","vghn", "n","bhjm", "m","njk,",
        "1","2", "2","13", "3","24", "4","35", "5","46", "6","57", "7","68", "8","79", "9","80", "0","9-", "-","0=", "=","-",
        " "," "
    )

    ; QWERTZ (German)
    LayoutMaps["QWERTZ"] := Map(
        "q","wa", "w","qase", "e","wsdr", "r","edft", "t","rfgy", "z","tghu", "u","zhji", "i","ujko", "o","iklp", "p","olü",
        "a","qwsy", "s","qweadzy", "d","wersfcx", "f","ertdgvc", "g","rtyfhvb", "h","tzugjbn", "j","zuihkmn", "k","uiojlm,", "l","iopkö",
        "y","asx", "x","ysdc", "c","xdfv", "v","cfgb", "b","vghn", "n","bhjm", "m","njk,",
        "1","2", "2","13", "3","24", "4","35", "5","46", "6","57", "7","68", "8","79", "9","80", "0","9ß", "ß","0",
        " "," "
    )

    ; AZERTY (French)
    LayoutMaps["AZERTY"] := Map(
        "a","zq", "z","azse", "e","zsdr", "r","edft", "t","rfgy", "y","tghu", "u","yhji", "i","ujko", "o","iklp", "p","olm",
        "q","awsw", "s","aqzedxw", "d","zersfcx", "f","ertdgvc", "g","rtyfhvb", "h","tyugjbn", "j","yuihk,n", "k","uiojlm;", "l","iopk:!",
        "w","qsx", "x","wsdc", "c","xdfv", "v","cfgb", "b","vghn", "n","bhj;",
        "1","2", "2","13", "3","24", "4","35", "5","46", "6","57", "7","68", "8","79", "9","80", "0","9",
        " "," "
    )
}

Esc::Reload
