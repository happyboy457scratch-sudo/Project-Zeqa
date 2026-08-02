/**
 * Evaluates trade equality between two offer sets.
 * @param {Array} leftItems - Array of cosmetic objects offered by Player 1
 * @param {Array} rightItems - Array of cosmetic objects offered by Player 2
 * @param {number} fairThreshold - Percentage difference allowed for a 'Fair' outcome (default 5%)
 * @returns {Object} Comprehensive trade calculation metrics
 */
export function compare(leftItems = [], rightItems = [], fairThreshold = 0.05) {
  const sumValues = items => items.reduce((total, item) => total + (item.value || 0), 0);
  
  const leftTotal = sumValues(leftItems);
  const rightTotal = sumValues(rightItems);
  const diff = leftTotal - rightTotal;
  
  const maxTotal = Math.max(leftTotal, rightTotal);
  const percentDiff = maxTotal > 0 ? Math.abs(diff) / maxTotal : 0;
  
  let outcome = 'Fair';
  if (percentDiff > fairThreshold) {
    outcome = diff > 0 ? 'Win for Left' : 'Win for Right';
  }

  return {
    leftTotal,
    rightTotal,
    difference: diff,
    percentageDifference: (percentDiff * 100).toFixed(1),
    outcome,
    isFair: outcome === 'Fair'
  };
}
