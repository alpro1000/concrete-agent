export const formatCurrency = (value, currency = 'CZK') => {
  if (value == null || Number.isNaN(Number(value))) {
    return '-';
  }

  return new Intl.NumberFormat('cs-CZ', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(Number(value));
};

export const formatNumber = (value, options = {}) => {
  if (value == null || Number.isNaN(Number(value))) {
    return '-';
  }

  return new Intl.NumberFormat('cs-CZ', {
    maximumFractionDigits: 2,
    ...options,
  }).format(Number(value));
};
