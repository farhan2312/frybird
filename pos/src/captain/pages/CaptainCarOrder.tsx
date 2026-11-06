import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, ClipboardList, Loader2, Minus, Plus, UtensilsCrossed } from 'lucide-react';
import { Button, cn, showToast, Spinner } from '@ury/ui';
import { formatCurrency } from '@ury/core';
import CaptainMenu from '../components/CaptainMenu';
import { CAR_ORDER_PREFIX, carOrderComment, carPlateFrom } from '../lib/captain-car-api';
import { DEFAULT_ORDER_TYPE } from '../../data/order-types';
import { syncOrder, type SyncOrderRequest } from '../../lib/order-api';
import { useRootStore, type RootState } from '../../store/root-store';
import { usePOSStore } from '../../store/pos-store';

const WALK_IN_CUSTOMER = 'Walk-In Customer';
const CARS_TAB_ROUTE = '/order?tab=cars';

/**
 * A captain's order for a customer in a car: no table, just the number plate. `/order/car` starts a new
 * one and `/order/car/:invoice` adds to one already sent. Saved as a Take Away order, so the cashier
 * bills it from Orders like any other.
 */
export default function CaptainCarOrder() {
  const { invoice } = useParams<{ invoice: string }>();
  const navigate = useNavigate();
  const user = useRootStore((state: RootState) => state.user);
  const {
    activeOrders,
    updateQuantity,
    removeFromOrder,
    posProfile,
    paymentModes,
    orderComment,
    setOrderComment,
    orderId,
    isUpdatingOrder,
    lastModifiedTime,
    selectedCustomer,
    orderLoading,
    loadTableOrder,
    clearTableOrder,
  } = usePOSStore();

  const [mode, setMode] = useState<'menu' | 'order'>('menu');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const carPlate = carPlateFrom(orderComment) ?? '';
  const total = activeOrders.reduce((sum, item) => sum + item.price * item.quantity, 0);
  const itemCount = activeOrders.reduce((sum, item) => sum + item.quantity, 0);

  useEffect(() => {
    clearTableOrder();
    if (invoice) loadTableOrder('', invoice);
    return () => clearTableOrder();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [invoice]);

  const handleSend = async () => {
    if (!carPlate.trim()) {
      showToast.error('Enter the car number plate before sending the order.');
      return;
    }
    if (!posProfile || !user?.name) {
      showToast.error('POS profile not found.');
      return;
    }
    if (activeOrders.length === 0) {
      showToast.error('Add at least one item before sending the order.');
      return;
    }

    setIsSubmitting(true);
    try {
      const orderData: SyncOrderRequest = {
        items: activeOrders.map((item) => ({
          item: item.id,
          item_name: item.name,
          rate: item.selectedVariant?.price || item.price,
          qty: item.quantity,
          comment: item.comment || undefined,
        })),
        no_of_pax: 1,
        pos_profile: posProfile.name,
        order_type: DEFAULT_ORDER_TYPE,
        customer: selectedCustomer?.name || WALK_IN_CUSTOMER,
        cashier: posProfile.cashier,
        owner: posProfile.owner,
        mode_of_payment: paymentModes[0],
        last_invoice: isUpdatingOrder ? orderId : null,
        last_modified_time: isUpdatingOrder ? lastModifiedTime || undefined : undefined,
        invoice: isUpdatingOrder ? orderId : null,
        waiter: user.name,
        comments: carOrderComment(carPlate),
      };
      const result = await syncOrder(orderData);
      if (result?.message && typeof result.message === 'object' && 'status' in result.message && result.message.status === 'Failure') {
        showToast.error('Failed to send the order. Please try again.');
        return;
      }
      clearTableOrder();
      showToast.success(isUpdatingOrder ? 'Order updated.' : 'Order sent to kitchen.');
      navigate(CARS_TAB_ROUTE);
    } catch (error) {
      console.error('Failed to send car order:', error);
      showToast.error(error instanceof Error ? error.message : 'Failed to send the order.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (orderLoading && invoice) {
    return <Spinner message="Loading order..." />;
  }

  return (
    <div className="flex h-screen flex-col bg-gray-50">
      <div className="flex items-center justify-between border-b border-gray-200 bg-white p-3">
        <div className="flex items-center">
          <Button onClick={() => navigate(CARS_TAB_ROUTE)} variant="ghost" size="icon" aria-label="Back to cars">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="ml-2 font-semibold text-gray-900">{invoice ? 'Car order' : 'New car order'}</h1>
        </div>
        <div className="flex rounded-full bg-gray-100 p-1">
          {(['menu', 'order'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setMode(tab)}
              className={cn(
                'flex items-center rounded-full px-3 py-1 text-sm font-medium',
                mode === tab ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600'
              )}
            >
              {tab === 'menu' ? <UtensilsCrossed className="mr-1 h-4 w-4" /> : <ClipboardList className="mr-1 h-4 w-4" />}
              {tab === 'menu' ? 'Menu' : `Order (${itemCount})`}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white p-3">
        <label htmlFor="car-plate" className="mb-1 block text-sm font-medium text-gray-700">
          Car number plate
        </label>
        <input
          id="car-plate"
          value={carPlate}
          onChange={(e) => {
            const plate = e.target.value.toUpperCase().replace(/[^A-Z0-9 -]/g, '').slice(0, 20);
            setOrderComment(plate ? CAR_ORDER_PREFIX + plate : '');
          }}
          placeholder="e.g. A 12345"
          className="h-11 w-full rounded-lg border border-gray-300 px-3 text-base font-semibold"
        />
      </div>

      <div className="flex flex-1 flex-col overflow-hidden">
        {mode === 'menu' ? (
          <CaptainMenu canAddItems />
        ) : (
          <div className="flex-1 overflow-y-auto p-3">
            {activeOrders.length === 0 && <p className="py-12 text-center text-gray-500">No items added yet.</p>}
            {activeOrders.map((item) => (
              <div key={item.uniqueId} className="mb-2 flex items-center justify-between rounded-lg bg-white p-3">
                <div className="mr-3 min-w-0">
                  <p className="text-sm font-medium text-gray-900">{item.name}</p>
                  <p className="text-xs text-gray-500">{formatCurrency(item.price * item.quantity)}</p>
                </div>
                <div className="flex shrink-0 items-center">
                  <button
                    aria-label="Decrease"
                    onClick={() =>
                      item.quantity <= 1 ? removeFromOrder(item.uniqueId!) : updateQuantity(item.uniqueId!, item.quantity - 1)
                    }
                    className="flex h-9 w-9 items-center justify-center rounded-full border border-gray-300"
                  >
                    <Minus className="h-4 w-4" />
                  </button>
                  <span className="w-8 text-center">{item.quantity}</span>
                  <button
                    aria-label="Increase"
                    onClick={() => updateQuantity(item.uniqueId!, item.quantity + 1)}
                    className="flex h-9 w-9 items-center justify-center rounded-full border border-gray-300"
                  >
                    <Plus className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {mode === 'order' && (
      <div className="border-t border-gray-200 bg-white p-3">
        <div className="mb-2 flex items-center justify-between px-1">
          <span className="text-sm font-semibold text-gray-700">Total</span>
          <span className="text-lg font-semibold text-gray-900">{formatCurrency(total)}</span>
        </div>
        <Button onClick={handleSend} size="lg" className="h-12 w-full text-base" disabled={isSubmitting || activeOrders.length === 0}>
          {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : isUpdatingOrder ? 'Update Order' : 'Send Order'}
        </Button>
      </div>
      )}
    </div>
  );
}
