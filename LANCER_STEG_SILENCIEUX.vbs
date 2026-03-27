' Lance STEG PV en arrière-plan (sans fenêtre console visible)
Set oShell = CreateObject("WScript.Shell")
oShell.Run "cmd /c cd /d """ & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & """ && python launcher.py", 1, False
