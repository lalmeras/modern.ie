#! /bin/sh

PowerShell -NoLogo -NonInteractive -ExecutionPolicy unrestricted -Command - <<'EOF'
Write-Output "Set network connection to private"
$networkListManager = [Activator]::CreateInstance([Type]::GetTypeFromCLSID([Guid]"{DCB00C01-570F-4A9B-8D69-199FDBA5723B}")) ;
$connections = $networkListManager.GetNetworkConnections() ;
$connections | % {$_.GetNetwork().SetCategory(1)}

Write-Output "Configure winrm"
$WINRM_EXEC = "$env:SYSTEMROOT\System32\winrm"
& $WINRM_EXEC "quickconfig" "-q"
& $WINRM_EXEC 'set' 'winrm/config/winrs' '@{MaxMemoryPerShellMB="300"}'
& $WINRM_EXEC 'set' 'winrm/config' '@{MaxTimeoutms="1800000"}'
& $WINRM_EXEC 'set' 'winrm/config/client/auth' '@{Basic="true"}'
& $WINRM_EXEC 'set' 'winrm/config/service' '@{AllowUnencrypted="true"}'
& $WINRM_EXEC 'set' 'winrm/config/service/auth' '@{Basic="true"}'
EOF
