@echo off
echo MSI Time Clock Windows Build Script
echo =================================

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found! Please install Python 3.8 or higher.
    exit /b 1
)

REM Install build dependencies
echo Installing build dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install requirements
    pause
    exit /b 1
)

python -m pip install pyinstaller
if errorlevel 1 (
    echo Failed to install pyinstaller
    pause
    exit /b 1
)
REM No need to install Pillow separately as it's already in requirements.txt
)

echo Dependencies installed successfully

REM Create version info file
echo Creating version info file...
echo VSVersionInfo( > file_version_info.txt
echo     ffi=FixedFileInfo( >> file_version_info.txt
echo         filevers=(1, 0, 0, 0), >> file_version_info.txt
echo         prodvers=(1, 0, 0, 0), >> file_version_info.txt
echo         mask=0x3f, >> file_version_info.txt
echo         flags=0x0, >> file_version_info.txt
echo         OS=0x40004, >> file_version_info.txt
echo         fileType=0x1, >> file_version_info.txt
echo         subtype=0x0, >> file_version_info.txt
echo         date=(0, 0) >> file_version_info.txt
echo     ), >> file_version_info.txt
echo     kids=[ >> file_version_info.txt
echo         StringFileInfo( >> file_version_info.txt
echo             [ >> file_version_info.txt
echo                 StringTable( >> file_version_info.txt
echo                     u'040904B0', >> file_version_info.txt
echo                     [StringStruct(u'CompanyName', u'Metro Staff Inc'), >> file_version_info.txt
echo                     StringStruct(u'FileDescription', u'MSI Time Clock'), >> file_version_info.txt
echo                     StringStruct(u'FileVersion', u'1.0.0'), >> file_version_info.txt
echo                     StringStruct(u'InternalName', u'MSITimeClock'), >> file_version_info.txt
echo                     StringStruct(u'LegalCopyright', u'Copyright (c) 2024 Metro Staff Inc'), >> file_version_info.txt
echo                     StringStruct(u'OriginalFilename', u'MSITimeClock.exe'), >> file_version_info.txt
echo                     StringStruct(u'ProductName', u'MSI Time Clock'), >> file_version_info.txt
echo                     StringStruct(u'ProductVersion', u'1.0.0')] >> file_version_info.txt
echo                 ) >> file_version_info.txt
echo             ] >> file_version_info.txt
echo         ), >> file_version_info.txt
echo         VarFileInfo([VarStruct(u'Translation', [1033, 1200])]) >> file_version_info.txt
echo     ] >> file_version_info.txt
echo ) >> file_version_info.txt

REM Convert PNG icon to ICO format
echo Converting application icon...
python -c "from PIL import Image; img = Image.open('assets/people-dark-bg.png'); img.save('app.ico')"

REM Clean previous build
echo Cleaning previous build...
rmdir /s /q build dist >nul 2>&1

REM Run PyInstaller
echo Building executable...
python -m PyInstaller --clean TimeClock.spec

REM Check if build was successful
if not exist "dist\MSITimeClock.exe" (
    echo Failed to create executable! Check the build output for errors.
    pause
    exit /b 1
)

REM Create installer
echo Creating installer...
echo RequestExecutionLevel admin > installer.nsi
echo !include "FileFunc.nsh" >> installer.nsi
echo !include "LogicLib.nsh" >> installer.nsi
echo !define PRODUCT_NAME "MSI Time Clock" >> installer.nsi
echo !define PRODUCT_VERSION "1.0.0" >> installer.nsi
echo !define PRODUCT_PUBLISHER "Metro Staff Inc" >> installer.nsi
echo !define PRODUCT_WEB_SITE "http://www.metrostaffing.net" >> installer.nsi
echo !define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\MSITimeClock.exe" >> installer.nsi
echo !define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" >> installer.nsi
echo. >> installer.nsi
echo Name "${PRODUCT_NAME}" >> installer.nsi
echo OutFile "MSITimeClockSetup.exe" >> installer.nsi
echo InstallDir "$PROGRAMFILES\MSI Time Clock" >> installer.nsi
echo InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" "" >> installer.nsi
echo ShowInstDetails show >> installer.nsi
echo ShowUnInstDetails show >> installer.nsi
echo. >> installer.nsi
echo Section "MainSection" SEC01 >> installer.nsi
echo    SetOutPath "$INSTDIR" >> installer.nsi
echo    SetOverwrite ifnewer >> installer.nsi
echo    File "dist\MSITimeClock.exe" >> installer.nsi
echo    File "settings.json" >> installer.nsi
echo    CreateDirectory "$SMPROGRAMS\MSI Time Clock" >> installer.nsi
echo    CreateShortCut "$SMPROGRAMS\MSI Time Clock\MSI Time Clock.lnk" "$INSTDIR\MSITimeClock.exe" >> installer.nsi
echo    CreateShortCut "$DESKTOP\MSI Time Clock.lnk" "$INSTDIR\MSITimeClock.exe" >> installer.nsi
echo    ; Create required directories >> installer.nsi
echo    CreateDirectory "$INSTDIR\logs" >> installer.nsi
echo    CreateDirectory "$INSTDIR\photos" >> installer.nsi
echo    CreateDirectory "$INSTDIR\data" >> installer.nsi
echo    ; Add assets directory >> installer.nsi
echo    CreateDirectory "$INSTDIR\assets" >> installer.nsi
echo    CreateDirectory "$INSTDIR\assets\fonts" >> installer.nsi
echo    SetOutPath "$INSTDIR\assets" >> installer.nsi
echo    File /r "dist\assets\*.*" >> installer.nsi
echo    ; Set permissions using cacls >> installer.nsi
echo    ExecWait 'cacls "$INSTDIR\logs" /E /T /G Users:F' >> installer.nsi
echo    ExecWait 'cacls "$INSTDIR\photos" /E /T /G Users:F' >> installer.nsi
echo    ExecWait 'cacls "$INSTDIR\data" /E /T /G Users:F' >> installer.nsi
echo SectionEnd >> installer.nsi
echo. >> installer.nsi
echo Section -Post >> installer.nsi
echo    WriteUninstaller "$INSTDIR\uninst.exe" >> installer.nsi
echo    WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\MSITimeClock.exe" >> installer.nsi
echo    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)" >> installer.nsi
echo    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe" >> installer.nsi
echo    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\MSITimeClock.exe" >> installer.nsi
echo    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}" >> installer.nsi
echo    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}" >> installer.nsi
echo    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}" >> installer.nsi
echo SectionEnd >> installer.nsi
echo. >> installer.nsi
echo Function un.onUninstSuccess >> installer.nsi
echo    HideWindow >> installer.nsi
echo    MessageBox MB_ICONINFORMATION^|MB_OK "$(^Name) was successfully removed from your computer." >> installer.nsi
echo FunctionEnd >> installer.nsi
echo. >> installer.nsi
echo Function un.onInit >> installer.nsi
echo    MessageBox MB_ICONQUESTION^|MB_YESNO^|MB_DEFBUTTON2 "Are you sure you want to completely remove $(^Name) and all of its components?" IDYES +2 >> installer.nsi
echo    Abort >> installer.nsi
echo FunctionEnd >> installer.nsi
echo. >> installer.nsi
echo Section Uninstall >> installer.nsi
echo    Delete "$INSTDIR\MSITimeClock.exe" >> installer.nsi
echo    Delete "$INSTDIR\*.dll" >> installer.nsi
echo    Delete "$INSTDIR\*.pyd" >> installer.nsi
echo    Delete "$INSTDIR\*.json" >> installer.nsi
echo    Delete "$INSTDIR\uninst.exe" >> installer.nsi
echo    Delete "$SMPROGRAMS\MSI Time Clock\MSI Time Clock.lnk" >> installer.nsi
echo    Delete "$DESKTOP\MSI Time Clock.lnk" >> installer.nsi
echo    RMDir /r "$INSTDIR\logs" >> installer.nsi
echo    RMDir /r "$INSTDIR\photos" >> installer.nsi
echo    RMDir /r "$INSTDIR\data" >> installer.nsi
echo    RMDir "$SMPROGRAMS\MSI Time Clock" >> installer.nsi
echo    RMDir /r "$INSTDIR" >> installer.nsi
echo    DeleteRegKey HKLM "${PRODUCT_UNINST_KEY}" >> installer.nsi
echo    DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}" >> installer.nsi
echo    SetAutoClose true >> installer.nsi
echo SectionEnd >> installer.nsi

REM Check if NSIS is installed
makensis /VERSION >nul 2>&1
if errorlevel 1 (
    echo NSIS not found! Please install NSIS to create the installer.
    echo Download from: https://nsis.sourceforge.io/Download
    echo Skipping installer creation...
) else (
    makensis installer.nsi
    echo Installer created: MSITimeClockSetup.exe
)

echo Build complete!
pause