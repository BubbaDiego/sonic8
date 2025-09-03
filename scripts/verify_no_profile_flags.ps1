Write-Host "Scanning repo for bad Chrome profile flags/paths..."
Select-String -Path . -Pattern '--profile-directory' -Recurse
Select-String -Path . -Pattern 'User Data' -Recurse
Write-Host "If any results show up above, remove those lines. Only user_data_dir must select the profile."

