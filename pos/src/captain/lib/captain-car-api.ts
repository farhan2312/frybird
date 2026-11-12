import { db } from '@ury/core';
import { DOCTYPES } from '../../data/doctypes';
import { DEFAULT_ORDER_TYPE } from '../../data/order-types';

// Same comment format QR curbside orders use (CURBSIDE_PREFIX in ury/ury/api/self_ordering.py),
// so the kitchen ticket and receipt show the plate for both.
export const CAR_ORDER_PREFIX = 'CURBSIDE - Car: ';

export const carOrderComment = (plate: string) => CAR_ORDER_PREFIX + plate.trim();

export const carPlateFrom = (comment: string | null | undefined) =>
  comment?.startsWith(CAR_ORDER_PREFIX) ? comment.slice(CAR_ORDER_PREFIX.length) : null;

export interface ActiveCarOrder {
  invoiceName: string;
  carPlate: string;
  createdAt: string;
  waiter: string;
  grandTotal: number;
  invoicePrinted: boolean;
}

interface CarInvoiceRow {
  name: string;
  custom_comments: string | null;
  creation: string;
  waiter: string;
  grand_total: number;
  invoice_printed: number;
}

/** Open orders matching the filters, oldest first so the longest wait is on top. */
async function getOpenOrders(filters: unknown[][]): Promise<ActiveCarOrder[]> {
  const rows = (await db.getDocList(DOCTYPES.POS_INVOICE, {
    fields: ['name', 'custom_comments', 'creation', 'waiter', 'grand_total', 'invoice_printed'],
    filters: [['docstatus', '=', 0], ...filters],
    orderBy: { field: 'creation', order: 'asc' },
    limit: '*' as unknown as number,
    asDict: true,
  } as unknown as Parameters<typeof db.getDocList>[1])) as CarInvoiceRow[];

  return rows.map((row) => ({
    invoiceName: row.name,
    carPlate: carPlateFrom(row.custom_comments) ?? '',
    createdAt: row.creation,
    waiter: row.waiter,
    grandTotal: row.grand_total,
    invoicePrinted: row.invoice_printed === 1,
  }));
}

/** Open orders for cars at this branch. */
export const getActiveCarOrders = (branch: string) =>
  getOpenOrders([['branch', '=', branch], ['custom_comments', 'like', `${CAR_ORDER_PREFIX}%`]]);

/** Open take away orders at this branch with no table and no car, from the captain or the counter. */
export async function getActiveTakeawayOrders(branch: string): Promise<ActiveCarOrder[]> {
  const orders = await getOpenOrders([
    ['branch', '=', branch],
    ['order_type', '=', DEFAULT_ORDER_TYPE],
    ['restaurant_table', 'is', 'not set'],
  ]);
  return orders.filter((order) => !order.carPlate);
}
