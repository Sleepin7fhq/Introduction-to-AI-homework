; Inno Setup 脚本：把整个包打包成 setup.exe
; 用法：装好 Inno Setup 6 后，右键本文件 -> Compile，即可在 installer\ 下生成 setup.exe
; 注意：编译前先运行 make-portable.cmd 内置 Node，setup.exe 才能完全自包含。

#define MyAppName "DSH 局域网共享网关"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "DSH Team"

[Setup]
AppId={{D7F0B2E4-9A6C-4F3E-8B1A-2C5E7D9F0A13}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\DSHLanShare
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\start-all.cmd
OutputDir=.
OutputBaseFilename=DSH-Lan-Share-Setup
; 压缩回退到极限压缩：node_modules 已打成单个 tar（见 [Files]），安装器只需写
; 少量大文件，固实压缩不再拖慢安装，却能保持 exe 尽量小。
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; 装到用户目录（LocalAppData），无需管理员权限；运行时网关要写自己的数据目录。
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
; 排除 node_modules 目录（避免 7 万小文件拖慢安装）；打包好的三个 node_modules.tar
; （alt/probe/runtime 下）会随 ..\* 一起进入安装包，首次启动由 start-all 解压。
; 同时排除运行时产物（*.log / logs 目录 / sessions.json）与 DSH 数据目录的运行时状态
; （sessions / storages / .credentials.yaml / .anonymous-user-id）：这些是运行期生成、
; 含机器绝对路径或凭据，绝不能随包分发——原始设计即"全新 dshhome 随包"。
Source: "..\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion; Excludes: "installer,node_modules,*.log,logs,sessions.json,sessions,storages,.credentials.yaml,.anonymous-user-id,*.jar,__pycache__,*.pyc,*.tmp"

[Icons]
Name: "{group}\启动 DSH 共享网关"; Filename: "{app}\start-all.cmd"; WorkingDir: "{app}"
Name: "{group}\卸载 DSH 共享网关"; Filename: "{uninstallexe}"
Name: "{autodesktop}\DSH 共享网关"; Filename: "{app}\start-all.cmd"; WorkingDir: "{app}"

[Run]
Filename: "{app}\start-all.cmd"; Description: "立即启动 DSH 共享网关"; Flags: postinstall nowait skipifsilent; WorkingDir: "{app}"

[UninstallDelete]
; 首次启动解压的 node_modules 与运行时数据是安装后才生成的，卸载器默认不清，
; 会残留约 800MB。这里显式整目录清空（审计 P3 卸载残留）。
Type: filesandordirs; Name: "{app}"
