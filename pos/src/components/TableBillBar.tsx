import { useCallback, useEffect, useState } from 'react';
import { Plus } from 'lucide-react';
import { Button, cn } from '@ury/ui';
import { formatCurrency } from '@ury/core';
import { getTableBills, type TableBill } from '../captain/lib/captain-table-api';
import { kotLabel } from '../lib/kot-label';

interface TableBillBarProps {
  table: string;
  /** The bill open now; null while a new bill is being taken. */
  currentInvoice: string | null;
  onOpenBill: (invoice: string) => void;
  onNewBill: () => void;
  /** Change it to reload the bills (after sending). */
  refreshKey?: unknown;
  disabled?: boolean;
}

/**
 * The bills on one table, for people paying separately: tap a bill to open it, or "+ New bill" to
 * take the next person's order on the same table. Hidden until the table has a bill.
 */
export default function TableBillBar({ table, currentInvoice, onOpenBill, onNewBill, refreshKey, disabled }: TableBillBarProps) {
  const [bills, setBills] = useState<TableBill[]>([]);

  const load = useCallback(async () => {
    try {
      setBills(await getTableBills(table));
    } catch (error) {
      console.error('Failed to load table bills', error);
    }
  }, [table]);

  useEffect(() => {
    load();
  }, [load, currentInvoice, refreshKey]);

  if (bills.length === 0) return null;
  const takingNewBill = !currentInvoice;

  const chip = (active: boolean) =>
    cn(
      'h-auto shrink-0 flex-col items-start gap-0 rounded-lg border px-3 py-1.5 text-left',
      active ? 'border-primary-600 bg-primary-50 text-primary-700' : 'border-gray-200 bg-white text-gray-700'
    );

  return (
    <div className="mt-2">
      <p className="mb-1 text-xs font-medium text-gray-500">Bills on this table</p>
      <div className="flex gap-2 overflow-x-auto pb-1">
        {bills.map((bill, index) => (
          <Button
            key={bill.name}
            variant="ghost"
            className={chip(bill.name === currentInvoice)}
            onClick={() => onOpenBill(bill.name)}
            disabled={disabled}
          >
            <span className="text-sm font-semibold">Bill {index + 1}</span>
            <span className="text-[11px] opacity-80">
              {kotLabel(bill.orderNo, bill.name)} · {formatCurrency(bill.grandTotal)}
            </span>
          </Button>
        ))}
        {takingNewBill ? (
          <div className={cn(chip(true), 'flex')} aria-current="true">
            <span className="text-sm font-semibold">Bill {bills.length + 1}</span>
            <span className="text-[11px] opacity-80">New, not sent</span>
          </div>
        ) : (
          <Button
            variant="outline"
            className="h-auto shrink-0 gap-1 rounded-lg border-dashed px-3 py-2 text-sm font-semibold text-primary-700"
            onClick={onNewBill}
            disabled={disabled}
          >
            <Plus className="h-4 w-4" />
            New bill
          </Button>
        )}
      </div>
    </div>
  );
}
