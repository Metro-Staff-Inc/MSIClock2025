RequestExecutionLevel admin 
!include "FileFunc.nsh" 
!include "LogicLib.nsh" 
!define PRODUCT_NAME "MSI Time Clock" 
!define PRODUCT_VERSION "1.0.0" 
!define PRODUCT_PUBLISHER "Metro Staff Inc" 
!define PRODUCT_WEB_SITE "http://www.metrostaffing.net" 
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\MSITimeClock.exe" 
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" 
 
Name "${PRODUCT_NAME}" 
OutFile "MSITimeClockSetup.exe" 
InstallDir "$PROGRAMFILES\MSI Time Clock" 
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" "" 
ShowInstDetails show 
ShowUnInstDetails show 
 
Section "MainSection" SEC01 
   SetOutPath "$INSTDIR" 
   SetOverwrite ifnewer 
   File "dist\MSITimeClock.exe" 
   File "settings.json" 
   CreateDirectory "$SMPROGRAMS\MSI Time Clock" 
   CreateShortCut "$SMPROGRAMS\MSI Time Clock\MSI Time Clock.lnk" "$INSTDIR\MSITimeClock.exe" 
   CreateShortCut "$DESKTOP\MSI Time Clock.lnk" "$INSTDIR\MSITimeClock.exe" 
   ; Create directories 
   CreateDirectory "$INSTDIR\logs" 
   CreateDirectory "$INSTDIR\photos" 
   CreateDirectory "$INSTDIR\data" 
   ; Set permissions using cacls 
   ExecWait 'cacls "$INSTDIR\logs" /E /T /G Users:F' 
   ExecWait 'cacls "$INSTDIR\photos" /E /T /G Users:F' 
   ExecWait 'cacls "$INSTDIR\data" /E /T /G Users:F' 
SectionEnd 
 
Section -Post 
   WriteUninstaller "$INSTDIR\uninst.exe" 
   WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\MSITimeClock.exe" 
   WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)" 
   WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe" 
   WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\MSITimeClock.exe" 
   WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}" 
   WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}" 
   WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}" 
SectionEnd 
 
Function un.onUninstSuccess 
   HideWindow 
   MessageBox MB_ICONINFORMATION|MB_OK "$(^Name) was successfully removed from your computer." 
FunctionEnd 
 
Function un.onInit 
   MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to completely remove $(^Name) and all of its components?" IDYES +2 
   Abort 
FunctionEnd 
 
Section Uninstall 
   Delete "$INSTDIR\MSITimeClock.exe" 
   Delete "$INSTDIR\*.dll" 
   Delete "$INSTDIR\*.pyd" 
   Delete "$INSTDIR\*.json" 
   Delete "$INSTDIR\uninst.exe" 
   Delete "$SMPROGRAMS\MSI Time Clock\MSI Time Clock.lnk" 
   Delete "$DESKTOP\MSI Time Clock.lnk" 
   RMDir /r "$INSTDIR\logs" 
   RMDir /r "$INSTDIR\photos" 
   RMDir /r "$INSTDIR\data" 
   RMDir "$SMPROGRAMS\MSI Time Clock" 
   RMDir /r "$INSTDIR" 
   DeleteRegKey HKLM "${PRODUCT_UNINST_KEY}" 
   DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}" 
   SetAutoClose true 
SectionEnd 
