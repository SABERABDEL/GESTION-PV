Set oShell = CreateObject("WScript.Shell")
Set oFSO = CreateObject("Scripting.FileSystemObject")
strDir = oFSO.GetParentFolderName(WScript.ScriptFullName)
strBat = strDir & "\LANCER_STEG.bat"
oShell.Run Chr(34) & strBat & Chr(34), 0, False
