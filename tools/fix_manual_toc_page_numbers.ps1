param(
    [Parameter(Mandatory = $true)]
    [string]$DocxPath,

    [ValidateSet("Physical", "Displayed")]
    [string]$PageNumberMode = "Physical",

    [ValidateRange(1, 5)]
    [int]$Passes = 2,

    [int]$PageOffset = 0
)

$ErrorActionPreference = "Stop"
$resolvedPath = (Resolve-Path -LiteralPath $DocxPath).Path

$wdActiveEndAdjustedPageNumber = 1
$wdCollapseStart = 1
$wdActiveEndPageNumber = 3
$pageInfoKind = if ($PageNumberMode -eq "Displayed") {
    $wdActiveEndAdjustedPageNumber
} else {
    $wdActiveEndPageNumber
}

function Normalize-HeadingKey {
    param([string]$Text)
    return ($Text -replace "\s+", " ").Trim().ToUpperInvariant()
}

function Get-TocTitle {
    param([string]$Text)
    return ($Text -replace "`t.*$", "").Trim()
}

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0

try {
    $doc = $word.Documents.Open($resolvedPath, $false, $false, $false)
    $headingPages = $null

    for ($pass = 1; $pass -le $Passes; $pass++) {
        $doc.Repaginate()

        $headingPages = @{}
        foreach ($paragraph in $doc.Paragraphs) {
            $styleName = $paragraph.Range.Style.NameLocal
            if ($styleName -eq "Heading 1" -or $styleName -eq "Heading 2") {
                $headingText = $paragraph.Range.Text.Trim()
                if (
                    $headingText -and
                    $headingText -ne "LIST OF FIGURES" -and
                    $headingText -ne "LIST OF ABBREVIATIONS" -and
                    $headingText -ne "TABLE OF CONTENTS"
                ) {
                    # TOC entries should point to where the heading starts. The default
                    # Range.Information call reports the active end of the paragraph,
                    # which can drift when a heading sits on a page boundary.
                    $headingStart = $paragraph.Range.Duplicate
                    $headingStart.Collapse($wdCollapseStart)
                    $page = $headingStart.Information($pageInfoKind) + $PageOffset
                    $key = Normalize-HeadingKey $headingText
                    if (-not $headingPages.ContainsKey($key)) {
                        $headingPages[$key] = $page
                    }
                }
            }
        }

        $insideToc = $false
        foreach ($paragraph in $doc.Paragraphs) {
            $text = $paragraph.Range.Text.Trim()
            if ($text -eq "TABLE OF CONTENTS") {
                $insideToc = $true
                continue
            }
            $styleName = $paragraph.Range.Style.NameLocal
            if (
                $insideToc -and
                (Normalize-HeadingKey $text) -eq "ABSTRACT" -and
                ($styleName -eq "Heading 1" -or $styleName -eq "Heading 2")
            ) {
                break
            }
            if ($insideToc -and $text) {
                $title = Get-TocTitle $text
                $key = Normalize-HeadingKey $title
                if ($headingPages.ContainsKey($key)) {
                    $targetText = "$title`t$($headingPages[$key])"
                    $entryRange = $paragraph.Range.Duplicate
                    $entryRange.End = $entryRange.End - 1
                    $entryRange.Text = $targetText
                }
            }
        }
    }

    $doc.Save()
    foreach ($entry in $headingPages.GetEnumerator() | Sort-Object Name) {
        Write-Output "$($entry.Name)`t$($entry.Value)"
    }
}
finally {
    if ($doc) {
        $doc.Close($false)
    }
    $word.Quit()
}
