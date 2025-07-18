export default function formatCurrency(value, fractionDigits = 2) {
  const amount = Number(value ?? 0);
  return amount.toLocaleString(undefined, {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits
  });
}
