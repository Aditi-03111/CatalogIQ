export const parseApiDate = (isoString?: string | null) => {
  if (!isoString) return null;
  try {
    const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/.test(isoString);
    const date = new Date(hasTimezone ? isoString : `${isoString}Z`);
    return isNaN(date.getTime()) ? null : date;
  } catch {
    return null;
  }
};

export const formatApiDateTime = (isoString?: string | null) => {
  const date = parseApiDate(isoString);
  if (!date || Number.isNaN(date.getTime())) return isoString || '-';

  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};
