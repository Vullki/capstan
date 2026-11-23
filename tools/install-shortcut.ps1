# Capstan: create a Desktop shortcut (and optionally a Start menu one) with the wolf icon.
# The shortcut carries the app's AppUserModelID, so the running window gets its own
# taskbar entry and icon (not grouped under Python), and pinning it works.
#
# Usage (run inside PowerShell, from the project folder):
#   Set-ExecutionPolicy -Scope Process Bypass; .\tools\install-shortcut.ps1 [-StartMenu]
#
# Built with the Unicode IShellLinkW API. The older WScript.Shell object saves paths
# as ANSI and breaks non-ASCII folder names (like this project's own).

param([switch]$StartMenu)
$ErrorActionPreference = 'Stop'

$root    = Split-Path -Parent $PSScriptRoot
$app     = Join-Path $root 'app'
$icon    = Join-Path $app 'ui\assets\capstan.ico'
$appId   = 'BlackWolf.Capstan'     # must match APP_ID in app/main.py
$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonw) { throw 'pythonw.exe not found on PATH. Install Python 3.11+ first.' }
if (-not (Test-Path -LiteralPath $app)) { throw "App folder not found: $app" }

if (-not ('CapstanLnk' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;

[ComImport, Guid("00021401-0000-0000-C000-000000000046")] class CShellLink {}

[ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("000214F9-0000-0000-C000-000000000046")]
interface IShellLinkW {
  void GetPath([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder f, int cch, IntPtr fd, uint flags);
  void GetIDList(out IntPtr ppidl);
  void SetIDList(IntPtr pidl);
  void GetDescription([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder s, int cch);
  void SetDescription([MarshalAs(UnmanagedType.LPWStr)] string s);
  void GetWorkingDirectory([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder s, int cch);
  void SetWorkingDirectory([MarshalAs(UnmanagedType.LPWStr)] string s);
  void GetArguments([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder s, int cch);
  void SetArguments([MarshalAs(UnmanagedType.LPWStr)] string s);
  void GetHotkey(out short k);
  void SetHotkey(short k);
  void GetShowCmd(out int c);
  void SetShowCmd(int c);
  void GetIconLocation([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder s, int cch, out int i);
  void SetIconLocation([MarshalAs(UnmanagedType.LPWStr)] string s, int i);
  void SetRelativePath([MarshalAs(UnmanagedType.LPWStr)] string s, uint r);
  void Resolve(IntPtr hwnd, uint flags);
  void SetPath([MarshalAs(UnmanagedType.LPWStr)] string s);
}

[ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("0000010b-0000-0000-C000-000000000046")]
interface IPersistFile {
  void GetClassID(out Guid c);
  [PreserveSig] int IsDirty();
  void Load([MarshalAs(UnmanagedType.LPWStr)] string f, uint mode);
  void Save([MarshalAs(UnmanagedType.LPWStr)] string f, bool remember);
  void SaveCompleted([MarshalAs(UnmanagedType.LPWStr)] string f);
  void GetCurFile([MarshalAs(UnmanagedType.LPWStr)] out string f);
}

[StructLayout(LayoutKind.Sequential, Pack = 4)] struct PropertyKey { public Guid fmtid; public uint pid; }
[StructLayout(LayoutKind.Explicit)] struct PropVariant { [FieldOffset(0)] public ushort vt; [FieldOffset(8)] public IntPtr p; }

[ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")]
interface IPropertyStore {
  void GetCount(out uint c);
  void GetAt(uint i, out PropertyKey k);
  void GetValue(ref PropertyKey k, out PropVariant v);
  void SetValue(ref PropertyKey k, ref PropVariant v);
  void Commit();
}

public static class CapstanLnk {
  public static void Create(string lnk, string target, string args, string workdir, string icon, string desc, string appId) {
    var link = new CShellLink();
    var sl = (IShellLinkW)link;
    sl.SetPath(target);
    sl.SetArguments(args);
    sl.SetWorkingDirectory(workdir);
    sl.SetIconLocation(icon, 0);
    sl.SetDescription(desc);
    var key = new PropertyKey { fmtid = new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), pid = 5 };  // System.AppUserModel.ID
    var v = new PropVariant { vt = 31, p = Marshal.StringToCoTaskMemUni(appId) };                    // VT_LPWSTR
    var store = (IPropertyStore)link;
    store.SetValue(ref key, ref v);
    store.Commit();
    Marshal.FreeCoTaskMem(v.p);
    ((IPersistFile)link).Save(lnk, true);
  }

  public static string Read(string lnk) {
    var link = new CShellLink();
    ((IPersistFile)link).Load(lnk, 0);
    var sl = (IShellLinkW)link;
    var a = new StringBuilder(1024); var b = new StringBuilder(1024); var c = new StringBuilder(1024); int i;
    sl.GetPath(a, a.Capacity, IntPtr.Zero, 0);
    sl.GetWorkingDirectory(b, b.Capacity);
    sl.GetIconLocation(c, c.Capacity, out i);
    return a + "|" + b + "|" + c;
  }
}
'@
}

function New-CapstanShortcut([string]$folder) {
  $lnk = Join-Path $folder 'Capstan.lnk'
  if (Test-Path -LiteralPath $lnk) { Remove-Item -LiteralPath $lnk -Force }
  [CapstanLnk]::Create($lnk, $pythonw, 'main.py', $app, $icon,
    'Find and download Hugging Face models, checked against your GPU first.', $appId)
  Write-Host "Shortcut: $lnk"
}

New-CapstanShortcut ([Environment]::GetFolderPath('Desktop'))
if ($StartMenu) { New-CapstanShortcut ([Environment]::GetFolderPath('Programs')) }
