# Building GameDrop for Windows

This guide explains how to build GameDrop as a Windows executable and create an installer.

## Prerequisites

1. Python 3.8 or higher
2. PyInstaller (`pip install pyinstaller`)
3. [Inno Setup](https://jrsoftware.org/isinfo.php) (for creating the installer)

## Building the Application

### Option 1: Using the Build Script (Recommended)

The simplest way to build the application is to use the included build script:

```powershell
# Navigate to the project root
cd path\to\gamedrop

# Run the build script
.\build_windows.bat
```

This script will:
1. Install required dependencies
2. Build the application using PyInstaller
3. Create an installer using Inno Setup (if installed)

### Option 2: Manual Build

#### Step 1: Build the executable with PyInstaller

```powershell
# Navigate to the project root
cd path\to\gamedrop

# Run PyInstaller with the Windows spec file
pyinstaller GameDrop_Windows.spec
```

This will create a folder called `dist\GameDrop` containing the application and all its dependencies.

#### Step 2: Create the installer with Inno Setup

1. Install Inno Setup from https://jrsoftware.org/isinfo.php
2. Compile the script file using the Inno Setup Compiler:

```powershell
# Replace with your Inno Setup installation path if different
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "installer\windows\gamedrop.iss"
```

The installer will be created in `installer\windows\output\GameDrop_Setup.exe`.

## Troubleshooting

### Logo/Assets Not Loading

If the application logo or other assets aren't loading correctly in the built application:

1. Verify the asset paths in `GameDrop_Windows.spec`:
   ```python
   datas=[
       ('gamedrop/assets', 'assets'),
       ('gamedrop', 'gamedrop'),
   ],
   ```

2. Check that the `resource_path` function in `gamedrop\utils\paths.py` is finding resources correctly.

### Installer Issues

If the installer isn't working or creating properly:
1. Verify Inno Setup is correctly installed
2. Check that all paths in `gamedrop.iss` are correct
3. Ensure the built application in `dist\GameDrop` works before creating the installer

## Notes

- The application will be installed in the user's program files directory by default
- The installer does not require administrator privileges
- A desktop shortcut can be created during installation (optional)
