Param(
  [Parameter(Mandatory=$true)]
  [string]$WalletId
)
python auto_core\launcher\open_jupiter.py --wallet-id $WalletId
