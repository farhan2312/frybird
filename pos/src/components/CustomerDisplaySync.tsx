import { useEffect } from 'react';
import { usePOSStore } from '../store/pos-store';
import { useRootStore } from '../store/root-store';

/**
 * Keeps the T2s's customer screen (see android/) showing the order on the cashier's screen: the cart being
 * built on POS, or the order open in Orders. Does nothing on devices without that screen.
 */
const CustomerDisplaySync = () => {
  const activeOrders = usePOSStore((state) => state.activeOrders);
  const { selectedOrder, selectedOrderItems } = useRootStore();

  useEffect(() => {
    const display = window.FryBirdPrinter?.updateCustomerDisplay;
    if (!display) return;

    let order;
    if (activeOrders.length > 0) {
      const lines = activeOrders.map((item) => ({
        name: item.name,
        qty: item.quantity,
        amount: item.price * item.quantity,
      }));
      order = { lines, discount: 0, total: lines.reduce((sum, line) => sum + line.amount, 0) };
    } else if (selectedOrder && selectedOrder.status !== 'Paid' && selectedOrder.status !== 'Recently Paid') {
      order = {
        lines: selectedOrderItems.map((item) => ({ name: item.item_name, qty: item.qty, amount: item.amount })),
        discount: selectedOrder.discount_amount ?? 0,
        total: selectedOrder.rounded_total || selectedOrder.grand_total,
      };
    } else {
      order = { lines: [], discount: 0, total: 0 };
    }
    window.FryBirdPrinter?.updateCustomerDisplay?.(JSON.stringify(order));
  }, [activeOrders, selectedOrder, selectedOrderItems]);

  return null;
};

export default CustomerDisplaySync;
