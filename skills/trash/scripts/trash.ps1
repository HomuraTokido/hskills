#Requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Position = 0, ValueFromRemainingArguments)]
    [string[]]$Path
)

$ShowHelp = $false
$DryRun = $false
$paths = @()

foreach ($a in $Path) {
    switch -Regex ($a) {
        '^(--help|-h|-help|-\?|/\?)$' { $ShowHelp = $true; break }
        '^(--dry-run|--dryrun|-n)$'  { $DryRun = $true; break }
        default { $paths += $a }
    }
}

if ($ShowHelp -or $paths.Count -eq 0) {
    Write-Host @"
trash - move files/directories to the Windows Recycle Bin (recoverable).

Usage:
  trash <path> [<path>...] [--dry-run] [--help]

  <path>...   one or more file/dir paths; wildcards supported
  --dry-run   show what would be trashed without deleting
  --help      show this help

Examples:
  trash .\build ./a.txt
  trash *.log
  trash --dry-run .\build
"@
    exit 0
}

Add-Type -AssemblyName Microsoft.VisualBasic -ErrorAction SilentlyContinue
$failed = $false

foreach ($p in $paths) {
    $items = @(Resolve-Path -Path $p -ErrorAction SilentlyContinue)
    if ($items.Count -eq 0) {
        Write-Warning "trash: no match for '$p'"
        $failed = $true
        continue
    }
    foreach ($item in $items) {
        $target = $item.Path
        try {
            if ($DryRun) {
                Write-Host "[dry-run] would trash: $target"
            }
            elseif (Test-Path -LiteralPath $target -PathType Container) {
                [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory($target, 'OnlyErrorDialogs', 'SendToRecycleBin')
                Write-Host "trashed: $target"
            }
            else {
                [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($target, 'OnlyErrorDialogs', 'SendToRecycleBin')
                Write-Host "trashed: $target"
            }
        }
        catch {
            Write-Error "trash: failed on '$target': $($_.Exception.Message)"
            $failed = $true
        }
    }
}

if ($failed) { exit 1 } else { exit 0 }
