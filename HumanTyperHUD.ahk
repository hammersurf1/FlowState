#Requires AutoHotkey v2.0
#SingleInstance Force
#MaxThreadsPerHotkey 2

; -------------------------------------------------------------------------
; CORE SETTINGS & INITIALIZATION
; -------------------------------------------------------------------------
Global IniFile := A_ScriptDir "\settings.ini"

; --- TUNED FOR REALISM ---
Global DefaultMeanDelay  := 35
Global DefaultVariance   := 45
Global DefaultTypoChance := 3
Global DefaultTypoDelay  := 125
Global DefaultRevChance  := 5   ; Base revision chance (will vary dynamically)

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
Global RevisionChance  := DefaultRevChance
Global SentencePause   := DefaultSentencePause
Global ParagraphPause  := DefaultParagraphPause
Global BrainstormFreq  := DefaultBrainstormFreq
Global EmojiPause      := DefaultEmojiPause
Global CurrentMomentum := 0 
Global LastEscTime     := 0

; State Variables
Global IsPaused := false
Global IsRunning := false

; Layout Maps
Global LayoutMaps := Map()
InitializeLayouts()

; HUD Globals
Global CurrentSettingIndex := 1
Global SettingsList := ["UserMeanDelay", "UserVariance", "TypoChance", "TypoDelay", "RevisionChance"]
Global SettingNames := ["Typing Speed (Lower is Faster)", "Variance (Lower is Consistent)", "Typo Chance (%)", "Typo Correction Speed", "Base Revision Chance (%)"]
Global DefaultsMap := Map("UserMeanDelay", DefaultMeanDelay, "UserVariance", DefaultVariance, "TypoChance", DefaultTypoChance, "TypoDelay", DefaultTypoDelay, "RevisionChance", DefaultRevChance)

; Load INI
if !FileExist(IniFile)
    SaveSettings()
else
    LoadSettings()

; -------------------------------------------------------------------------
; HUD LOGIC
; -------------------------------------------------------------------------
CycleHUD(Direction) {
    Global CurrentSettingIndex
    CurrentSettingIndex += Direction
    if (CurrentSettingIndex > SettingsList.Length)
        CurrentSettingIndex := 1
    if (CurrentSettingIndex < 1)
        CurrentSettingIndex := SettingsList.Length
    ShowHUD()
}

AdjustHUD(Direction) {
    Global UserMeanDelay, UserVariance, TypoChance, TypoDelay, RevisionChance, CurrentSettingIndex
    CurrentVar := SettingsList[CurrentSettingIndex]
    
    CurrentVal := 0
    Switch CurrentVar {
        Case "UserMeanDelay": CurrentVal := UserMeanDelay
        Case "UserVariance": CurrentVal := UserVariance
        Case "TypoChance": CurrentVal := TypoChance
        Case "TypoDelay": CurrentVal := TypoDelay
        Case "RevisionChance": CurrentVal := RevisionChance
    }

    Step := (CurrentVar = "TypoChance" || CurrentVar = "RevisionChance") ? 1 : (CurrentVar = "TypoDelay") ? 25 : 5
    NewVal := CurrentVal + (Direction > 0 ? Step : -Step)
    
    if (NewVal < 0)
        NewVal := 0
        
    Switch CurrentVar {
        Case "UserMeanDelay": UserMeanDelay := NewVal
        Case "UserVariance": UserVariance := NewVal
        Case "TypoChance": TypoChance := NewVal
        Case "TypoDelay": TypoDelay := NewVal
        Case "RevisionChance": RevisionChance := NewVal
    }
        
    SaveSettings()
    ShowHUD()
}

ShowHUD() {
    Global CurrentSettingIndex, SettingsList, SettingNames, DefaultsMap
    Global UserMeanDelay, UserVariance, TypoChance, TypoDelay, RevisionChance

    CurrentVar := SettingsList[CurrentSettingIndex]
    CurrentVal := 0
    
    Switch CurrentVar {
        Case "UserMeanDelay": CurrentVal := UserMeanDelay
        Case "UserVariance": CurrentVal := UserVariance
        Case "TypoChance": CurrentVal := TypoChance
        Case "TypoDelay": CurrentVal := TypoDelay
        Case "RevisionChance": CurrentVal := RevisionChance
    }

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
    IniWrite(RevisionChance,IniFile, "Settings", "RevisionChance")
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
    Global RevisionChance := IniRead(IniFile, "Settings", "RevisionChance", DefaultRevChance)
    Global SentencePause  := IniRead(IniFile, "Advanced", "SentencePauseMs", DefaultSentencePause)
    Global ParagraphPause := IniRead(IniFile, "Advanced", "ParagraphPauseMs", DefaultParagraphPause)
    Global BrainstormFreq := IniRead(IniFile, "Advanced", "BrainstormFrequency", DefaultBrainstormFreq)
    Global EmojiPause     := IniRead(IniFile, "Advanced", "EmojiPauseMs", DefaultEmojiPause)
}

; -------------------------------------------------------------------------
; GLOBAL HOTKEYS
; -------------------------------------------------------------------------
!Up::CycleHUD(1)
!Down::CycleHUD(-1)
!Right::AdjustHUD(1)
!Left::AdjustHUD(-1)

; -------------------------------------------------------------------------
; PRODUCTION TYPING ENGINE: Ctrl + Alt + V
; -------------------------------------------------------------------------
^!v::
{
    Global IsPaused, IsRunning, LastEscTime
    
    if (IsRunning) {
        IsPaused := !IsPaused
        return
    }

    if !A_Clipboard
        return

    IsRunning := true
    
    KeyWait "Ctrl"
    KeyWait "Shift"
    KeyWait "Alt"

    TargetWin := WinExist("A")
    ActiveLayout := DetectKeyboardLayout(TargetWin)
    NeighborMap := GetLayoutMap(ActiveLayout)

    TextToType := StrReplace(A_Clipboard, "`r`n", "`n")
    TotalLen := StrLen(TextToType)

    Blocker := InputHook("L0")
    Blocker.MinSendLevel := 2 
    Blocker.KeyOpt("{All}", "S")
    Blocker.KeyOpt("{Esc}", "-S")

    Blocker.OnKeyDown := (ih, vk, sc) => (
        (GetKeyState("Alt", "P")) ? (
            (GetKeyName(Format("vk{:x}sc{:x}", vk, sc)) = "Up")    ? CycleHUD(1) :
            (GetKeyName(Format("vk{:x}sc{:x}", vk, sc)) = "Down")  ? CycleHUD(-1) :
            (GetKeyName(Format("vk{:x}sc{:x}", vk, sc)) = "Right") ? AdjustHUD(1) :
            (GetKeyName(Format("vk{:x}sc{:x}", vk, sc)) = "Left")  ? AdjustHUD(-1) :
            ""
        ) : ""
    )

    Blocker.Start()

    CurrentMomentum := 0
    IsPaused := false
    LastEscTime := 0
    CurrentWordBuffer := "" 
    WordsTypedInSentence := 0 ; NEW: Tracks position in sentence
    i := 1
    
    While (i <= TotalLen)
    {
        ; --- PAUSE LOGIC ---
        if (IsPaused) {
            Blocker.Stop()
            ToolTip("⏸️ PAUSED")
            While (IsPaused) {
                if GetKeyState("Esc", "P") { 
                    if (A_TickCount - LastEscTime < 500) {
                        ToolTip("🔴 CANCELLED")
                        SetTimer () => ToolTip(), -2000
                        IsRunning := false
                        return
                    }
                    LastEscTime := A_TickCount
                    KeyWait "Esc" 
                }
                Sleep 50
            }
            ToolTip("▶️ RESUMING...")
            SetTimer () => ToolTip(), -1000
            WinActivate(TargetWin)
            Blocker.Start()
        }

        if GetKeyState("Esc", "P") {
            CurrentTime := A_TickCount
            if (CurrentTime - LastEscTime < 500) {
                Blocker.Stop()
                ToolTip("🔴 CANCELLED")
                SetTimer () => ToolTip(), -2000
                IsRunning := false
                return
            } else {
                IsPaused := true
                LastEscTime := CurrentTime
                KeyWait "Esc"
                continue
            }
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
            if (Neighbor != "") {
                RealizationDelay := Random(0, 3) 
                if (i + RealizationDelay >= TotalLen)
                    RealizationDelay := 0

                HumanKeystroke(Neighbor) 
                CurrentWordBuffer .= Neighbor
                
                Loop RealizationDelay {
                    BufferChar := SubStr(TextToType, i + A_Index, 1)
                    HumanKeystroke(BufferChar)
                    CurrentWordBuffer .= BufferChar
                    Sleep GaussianRandom(UserMeanDelay, UserVariance)
                }

                Sleep Random(TypoDelay * 2, TypoDelay * 4) 

                SetKeyDelay Random(30, 60), 10
                Loop (RealizationDelay + 1) {
                    SendEvent "{Backspace}"
                    CurrentWordBuffer := SubStr(CurrentWordBuffer, 1, StrLen(CurrentWordBuffer)-1)
                }
                SetKeyDelay 10, 10
                
                Sleep Random(100, 200)
                CurrentMomentum := 0
                continue 
            }
        }

        ; --- A. EMOJI & UNICODE ---
        if (CharCode >= 0xD800 && CharCode <= 0xDBFF) {
            Sleep Random(EmojiPause, EmojiPause + 500)
            FullEmoji := SubStr(TextToType, i, 2)
            SurgicalPaste(FullEmoji) 
            Sleep UserMeanDelay
            CurrentMomentum := 0 
            i += 2 
            CurrentWordBuffer := "" 
            continue
        }

        NextChar := (i < TotalLen) ? SubStr(TextToType, i+1, 1) : ""

        ; -----------------------------------------------------------------------
        ; REVISION LOGIC (UPDATED WITH SENTENCE POSITION & SPECIFIC TIMING)
        ; -----------------------------------------------------------------------
        IsSeparator := (Char = " " || Char = "." || Char = "," || Char = "!" || Char = "?" || Char = "`n" || Char = "`t" || Char = ";" || Char = ":")
        IsRevisionTrigger := (Char = " ")
        
        if (IsRevisionTrigger && StrLen(CurrentWordBuffer) > 3) {
            ; CALCULATE DYNAMIC CHANCE BASED ON SENTENCE POSITION
            CurrentRevChance := RevisionChance
            
            if (WordsTypedInSentence < 2) {
                ; High chance at start of sentence (Finding the right start)
                CurrentRevChance := RevisionChance * 2 
            } else if (WordsTypedInSentence > 6) {
                ; Low chance in middle/end (Flow state)
                CurrentRevChance := Floor(RevisionChance / 2)
            }

            if (Random(1, 100) <= CurrentRevChance) {
                ; 1. THE "SUDDEN STOP" (Word Doubt) - User requested 400-800ms
                Sleep Random(400, 800) 

                ; 2. DELETE THE WORD
                SetKeyDelay Random(40, 70), 10
                Loop StrLen(CurrentWordBuffer) {
                    SendEvent "{Backspace}"
                }
                SetKeyDelay 10, 10
                CurrentWordBuffer := "" 

                ; 3. THE "RESET" PAUSE (Cognitive Reload) - User requested 600-1200ms
                Sleep Random(600, 1200)

                ; 4. RETYPE THE WORD
                WordStart := i - 1
                Loop {
                    CheckChar := SubStr(TextToType, WordStart, 1)
                    if (CheckChar = " " || CheckChar = "`n" || CheckChar = "`t" || WordStart < 1) {
                        WordStart++ 
                        break
                    }
                    WordStart--
                }
                WordToRetype := SubStr(TextToType, WordStart, i - WordStart)

                Loop Parse, WordToRetype {
                    HumanKeystroke(A_LoopField)
                    Sleep GaussianRandom(UserMeanDelay, UserVariance)
                }
                CurrentMomentum := 0 
            }
            CurrentWordBuffer := "" 
            WordsTypedInSentence++ ; Increment word count
        }
        else if (IsSeparator) {
            CurrentWordBuffer := ""
            if (Char != " ") 
                WordsTypedInSentence++
        }
        else {
            CurrentWordBuffer .= Char 
        }

        ; --- B. COGNITIVE PAUSES & SENTENCE RESET ---
        if (Char = "." || Char = "?" || Char = "!") && (NextChar = " " || NextChar = "`n") {
            HumanKeystroke(Char)
            Sleep Random(SentencePause, SentencePause + 400) 
            CurrentMomentum := 0 
            WordsTypedInSentence := 0 ; RESET SENTENCE COUNTER
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
            WordsTypedInSentence := 0 ; RESET SENTENCE COUNTER
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

    ToolTip("✅ DONE`n🔒 Keyboard still locked.`n👉 Press [ESC] to unlock.")
    SoundBeep 600, 150 
    KeyWait "Esc", "D" 
    KeyWait "Esc"
    Blocker.Stop() 
    SendEvent "{LCtrl up}{RCtrl up}{LAlt up}{RAlt up}{LShift up}{RShift up}{LWin up}{RWin up}"
    IsRunning := false 
    ToolTip("🔓 KEYBOARD UNLOCKED")
    SetTimer () => ToolTip(), -2000
}

; -------------------------------------------------------------------------
; HELPERS
; -------------------------------------------------------------------------
HumanKeystroke(Char) {
    DwellTime := Random(10, 40)
    SetKeyDelay 0, DwellTime
    if IsUpper(Char) && Char != " " {
        if (Random(1, 10) > 7)
            SetKeyDelay 0, DwellTime + Random(20, 50)
    }

    SendEvent "{Text}" Char
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
    u1 := Random(0.0000001, 1.0) ; Prevent Log(0)
    u2 := Random(0.0, 1.0)
    ; Box-Muller transform
    z0 := Sqrt(-2.0 * Log(u1)) * Cos(2.0 * 3.141592653589793 * u2)
    Return Floor(Mean + (z0 * StdDev))
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
    LayoutMaps["QWERTY"] := Map(
        "q","wa", "w","qase", "e","wsdr", "r","edft", "t","rfgy", "y","tghu", "u","yhji", "i","ujko", "o","iklp", "p","ol",
        "a","qwsz", "s","qweadzx", "d","wersfcx", "f","ertdgvc", "g","rtyfhvb", "h","tyugjbn", "j","yuihkmn", "k","uiojlm,", "l","iopk;",
        "z","asx", "x","zsdc", "c","xdfv", "v","cfgb", "b","vghn", "n","bhjm", "m","njk,",
        "1","2", "2","13", "3","24", "4","35", "5","46", "6","57", "7","68", "8","79", "9","80", "0","9-", "-","0=", "=","-",
        " "," "
    )
    LayoutMaps["QWERTZ"] := Map(
        "q","wa", "w","qase", "e","wsdr", "r","edft", "t","rfgy", "z","tghu", "u","zhji", "i","ujko", "o","iklp", "p","olü",
        "a","qwsy", "s","qweadzy", "d","wersfcx", "f","ertdgvc", "g","rtyfhvb", "h","tzugjbn", "j","zuihkmn", "k","uiojlm,", "l","iopkö",
        "y","asx", "x","ysdc", "c","xdfv", "v","cfgb", "b","vghn", "n","bhjm", "m","njk,",
        "1","2", "2","13", "3","24", "4","35", "5","46", "6","57", "7","68", "8","79", "9","80", "0","9ß", "ß","0",
        " "," "
    )
    LayoutMaps["AZERTY"] := Map(
        "a","zq", "z","azse", "e","zsdr", "r","edft", "t","rfgy", "y","tghu", "u","yhji", "i","ujko", "o","iklp", "p","olm",
        "q","awsw", "s","aqzedxw", "d","zersfcx", "f","ertdgvc", "g","rtyfhvb", "h","tyugjbn", "j","yuihk,n", "k","uiojlm;", "l","iopk:!",
        "w","qsx", "x","wsdc", "c","xdfv", "v","cfgb", "b","vghn", "n","bhj;",
        "1","2", "2","13", "3","24", "4","35", "5","46", "6","57", "7","68", "8","79", "9","80", "0","9",
        " "," "
    )
}