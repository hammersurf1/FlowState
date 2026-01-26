#Requires AutoHotkey v2.0
#SingleInstance Force

; -------------------------------------------------------------------------
; CORE SETTINGS & INITIALIZATION
; -------------------------------------------------------------------------
Global IniFile := A_ScriptDir "\settings.ini"

; Defaults
Global DefaultMeanDelay  := 60
Global DefaultVariance   := 25
Global DefaultTypoChance := 4
Global DefaultTypoDelay  := 150

; Cognitive Defaults
Global DefaultSentencePause  := 1200
Global DefaultParagraphPause := 2000
Global DefaultBrainstormFreq := 60
Global DefaultEmojiPause     := 1800 

; Runtime Vars
Global UserMeanDelay    := DefaultMeanDelay
Global UserVariance     := DefaultVariance
Global TypoChance       := DefaultTypoChance
Global TypoDelay        := DefaultTypoDelay
Global SentencePause    := DefaultSentencePause
Global ParagraphPause   := DefaultParagraphPause
Global BrainstormFreq   := DefaultBrainstormFreq
Global EmojiPause       := DefaultEmojiPause
Global CurrentMomentum  := 0 

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
; PRODUCTION TYPING ENGINE: Ctrl + Alt + V
; -------------------------------------------------------------------------
^!v::
{
    if !A_Clipboard
        return

    KeyWait "Ctrl"
    KeyWait "Shift"

    TargetWin := WinExist("A")
    ActiveLayout := DetectKeyboardLayout(TargetWin)
    NeighborMap := GetLayoutMap(ActiveLayout)

    TextToType := StrReplace(A_Clipboard, "`r`n", "`n")
    TotalLen := StrLen(TextToType)

    if (TotalLen > 5000) {
        if (MsgBox("Type " TotalLen " chars?", "Large Paste", "YesNo IconExclamation") = "No")
            return
    }

    CurrentMomentum := 0
    i := 1
    SetKeyDelay 0, 20 

    While (i <= TotalLen)
    {
        if GetKeyState("Esc", "P") {
            ToolTip("🔴 CANCELLED")
            SetTimer () => ToolTip(), -2000
            return
        }

        if !WinActive(TargetWin)
            WinActivate(TargetWin)

        Char := SubStr(TextToType, i, 1)
        CharCode := Ord(Char)
        
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
            SimulateKeystroke(Char)
            Sleep Random(SentencePause, SentencePause + 400) 
            CurrentMomentum := 0 
            i++
            continue
        }

        if (Char = "," || Char = ";") {
            SimulateKeystroke(Char)
            Sleep Random(300, 600) 
            CurrentMomentum := Max(0, CurrentMomentum - 5)
            i++
            continue
        }

        if (Char = " " && Random(1, BrainstormFreq) = 1) {
            Sleep Random(1500, 4000) 
            CurrentMomentum := 0 
        }

        ; --- C. ADVANCED TYPO LOGIC ---
        if (CharCode < 128 && Char != " " && Char != "`n" && Random(1, 100) <= TypoChance)
        {
            if (i < TotalLen && NextChar != " " && Random(1, 100) <= 40) {
                SimulateKeystroke(NextChar)
                Sleep GaussianRandom(UserMeanDelay - CurrentMomentum, UserVariance)
                SimulateKeystroke(Char)
                Sleep Random(TypoDelay, TypoDelay + 200) 
                SendEvent "{Backspace 2}"
                Sleep Random(50, 100)
                CurrentMomentum := 0
                continue 
            }
            
            Neighbor := GetNeighbor(Char, NeighborMap)
            if (Neighbor != "")
            {
                SimulateKeystroke(Neighbor)
                Sleep Random(TypoDelay, TypoDelay + 200)
                SendEvent "{Backspace}"
                Sleep Random(50, 100)
                CurrentMomentum := 0
            }
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
            SimulateKeystroke(Char)
            if (CurrentMomentum < 15)
                CurrentMomentum += 0.5
        }

        ; --- E. TIMING ---
        CalcMean := UserMeanDelay - CurrentMomentum
        if (InStr("th,he,in,er,an,re,on,at,en,nd,ti,es,or,te,of,ed,is,it,al,ar,st,to,nt", StrLower(Char . NextChar)))
            CalcMean -= 10

        FinalDelay := GaussianRandom(CalcMean, UserVariance)
        if (FinalDelay < 20)
            FinalDelay := 20
        if (FinalDelay > 250)
            FinalDelay := 250

        Sleep FinalDelay
        i++ 
    }

    ; --- FINISHED TOOLTIP ---
    ToolTip("✅ DONE")
    SetTimer () => ToolTip(), -2000
}

; -------------------------------------------------------------------------
; HELPERS
; -------------------------------------------------------------------------

SimulateKeystroke(Char) {
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