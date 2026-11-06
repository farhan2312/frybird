import { db } from '@ury/core';
import { DOCTYPES } from '../../data/doctypes';

// Same comment format QR curbside orders use (CURBSIDE_PREFIX in ury/ury/api/self_ordering.py),
// so the kitchen ticket and receipt show the plate for both.
export const CAR_ORDER_PREFIX = 'CURBSIDE - Car: ';

export const carOrderComment = (plate: string) => CAR_ORDER_PREFIX + plate.trim();

export const carPlateFrom = (comment: string | null | undefined) =>
  comment?.startsWith(CAR_ORDER_PREFIX) ? comment.slice(CAR_ORDER_PREFIX.length) : null;

export interface ActiveCarOrder {
  invoiceName: string;
  carPlate: string;
  waiter: string;
  grandTotal: number;
  invoicePrinted: boolean;
}

interface CarInvoiceRow {
  name: string;
  custom_comments: string;
  waiter: string;
  grand_total: number;
  invoice_printed: number;
}

/** Open orders for cars at this branch, oldest first so the longest wait is on top. */
export async function getActiveCarOrders(branch: string): Promise<ActiveCarOrder[]> {
  const rows = (await db.getDocList(DOCTYPES.POS_INVOICE, {
    fields: ['name', 'custom_comments', 'waiter', 'grand_total', 'invoice_printed'],
    filters: [
      ['branch', '=', branch],
      ['docstatus', '=', 0],
      ['custom_comments', 'like', `${CAR_ORDER_PREFIX}%`],
    ],
    orderBy: { field: 'creation', order: 'asc' },
    limit: '*' as unknown as number,
    asDict: true,
  } as unknown as Parameters<typeof db.getDocList>[1])) as CarInvoiceRow[];

  return rows.map((row) => ({
    invoiceName: row.name,
    carPlate: carPlateFrom(row.custom_comments) ?? '',
    waiter: row.waiter,
    grandTotal: row.grand_total,
    invoicePrinted: row.invoice_printed === 1,
  }));
}
