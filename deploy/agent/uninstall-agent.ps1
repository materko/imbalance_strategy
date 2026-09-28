<#
.SYNOPSIS
    Zastaví a odstráni naplánovanú úlohu agenta hubu (protiklad install-agent.ps1).

.EXAMPLE
    .\deploy\agent\uninstall-agent.ps1
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$TaskName = "TradeBot agent"
)

$ErrorActionPreference = "Stop"
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -eq $task) { Write-Host "úloha '$TaskName' neexistuje"; exit 0 }

if ($PSCmdlet.ShouldProcess($TaskName, "Stop + Unregister-ScheduledTask")) {
    try { Stop-ScheduledTask -TaskName $TaskName -ErrorAction Stop } catch {}
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "OK: úloha '$TaskName' odstránená (agent sa už pri prihlásení nespustí; bežiace terminály NT/MT5 to nezavrie)"
}
