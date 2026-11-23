/**
 * The number staff call an order by: the daily order number printed as "KOT# 41" on the
 * kitchen ticket. Falls back to the invoice number for orders that have none.
 */
export function kotLabel(orderNo: string | number | null | undefined, invoiceName: string): string {
  const no = orderNo == null ? '' : String(orderNo).trim();
  return no ? `KOT #${no}` : invoiceName;
}
