import { useRef, useState } from 'react';
import { showToast } from '@ury/ui';
import { usePOSStore } from '../store/pos-store';
import { useRootStore } from '../store/root-store';
import { cn } from '@ury/ui';
import { Button } from '@ury/ui';
import TableSelectionDialog from './TableSelectionDialog';
import { DEFAULT_ORDER_TYPE, DINE_IN, ORDER_TYPES , type OrderType} from '../data/order-types';
import { Car, HandPlatter } from 'lucide-react';
import { Input } from '@ury/ui';
import { CAR_ORDER_PREFIX, carOrderDraft, carPhoneFrom, carPlateFrom } from '../captain/lib/captain-car-api';
import { isUserRestrictedFromTableOrders } from '@ury/core';
import { formatMergedTableLabel } from '../lib/table-utils';
import { t } from '../i18n';

const CURBSIDE_VALUE = 'Curbside';
const CURBSIDE = { label: 'Curbside', value: CURBSIDE_VALUE as OrderType, icon: Car };

interface OrderTypeSelectProps {
  disabled?: boolean;
}

const OrderTypeSelect = ({ disabled }: OrderTypeSelectProps) => {
  const { selectedOrderType, setSelectedOrderType, setSelectedTable, selectedTable, tableOrder, posProfile, isUpdatingOrder, activeOrders, orderComment, setOrderComment } = usePOSStore();
  // Curbside is a Take Away order whose note is "CURBSIDE - Car: <plate>", as on the captain tablet.
  const isCurbside = selectedOrderType === 'Take Away' && carPlateFrom(orderComment) !== null;
  // While a saved order is open, the first tap on another order type with items in the cart only warns.
  const pendingSwitch = useRef<{ type: OrderType; at: number } | null>(null);
  const { user } = useRootStore();
  const [showTableDialog, setShowTableDialog] = useState(false);

  // Check if user is restricted from table orders
  const isRestrictedFromTableOrders = isUserRestrictedFromTableOrders(user, posProfile);

  const handleOrderTypeSelect = (type: OrderType) => {
    // Prevent selecting "Dine In" if user is restricted
    if (type === DINE_IN && isRestrictedFromTableOrders) {
      return;
    }
    
    if (type === selectedOrderType && type !== DINE_IN) {
      if (type === 'Take Away' && isCurbside) setOrderComment('');  // Curbside -> plain Take Away
      return;
    }

    if (isUpdatingOrder && !isInPlaceToggle(type)) {
      // A saved order is open in this tab. It stays saved on the server (Tables / Orders),
      // so the tab can start a new order of the chosen type instead of needing a new tab.
      const pending = pendingSwitch.current;
      const confirmed = pending?.type === type && Date.now() - pending.at < 5000;
      if (activeOrders.length > 0 && !confirmed) {
        pendingSwitch.current = { type, at: Date.now() };
        showToast.info('Tap again to start a new order. The current order stays saved; items not yet sent are removed.');
        return;
      }
      pendingSwitch.current = null;
      if (selectedTable) setSelectedTable(null, null);
    }

    setSelectedOrderType(type);
    if (carPlateFrom(usePOSStore.getState().orderComment) !== null) setOrderComment('');  // leaving Curbside
    if (type === DINE_IN) {
      setShowTableDialog(true);
    }
  };

  // Take Away <-> Delivery can change on the saved order itself when the profile allows it.
  function isInPlaceToggle(type: OrderType) {
    const toggleable = (v: string) => v === 'Take Away' || v === 'Delivery';
    return Boolean(posProfile?.edit_order_type) && toggleable(selectedOrderType) && toggleable(type);
  }

  const handleCurbside = () => {
    if (isCurbside) return;
    if (selectedOrderType !== 'Take Away') handleOrderTypeSelect('Take Away');
    // Read the store again: switching away from a saved order may need a second tap first.
    if (usePOSStore.getState().selectedOrderType === 'Take Away') setOrderComment(CAR_ORDER_PREFIX);
  };

  const handleTableDialogClose = () => {
    setShowTableDialog(false);
    // Use a timeout to allow state to update before checking
    setTimeout(() => {
      const currentState = usePOSStore.getState();
      if (currentState.selectedOrderType === DINE_IN && !currentState.selectedTable) {
        setSelectedOrderType(DEFAULT_ORDER_TYPE);
      }
    }, 100);
  };

  const tableDisplayLabel =
    selectedTable && tableOrder?.message?.restaurant_table
      ? formatMergedTableLabel(
          tableOrder.message.restaurant_table,
          tableOrder.message.custom_merged_tables
        )
      : selectedTable;

  return (
    <div>
      <div className="flex gap-2 overflow-x-auto pb-2 -mx-2 px-2">
        {ORDER_TYPES.flatMap((type) => (type.value === 'Take Away' ? [type, CURBSIDE] : [type])).map(({ value, icon: Icon }) => {
          if (value === CURBSIDE_VALUE) {
            return (
              <Button
                key="curbside"
                onClick={handleCurbside}
                variant={isCurbside ? 'default' : 'outline'}
                className={cn(
                  'h-fit flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap bg-white border transition-colors',
                  isCurbside
                    ? 'text-primary-700 bg-primary-50 border-primary-600 hover:bg-primary-50'
                    : 'text-gray-700 border-gray-200 hover:bg-gray-50',
                  disabled && 'opacity-50 cursor-not-allowed'
                )}
                disabled={disabled}
              >
                <Car className="w-4 h-4" />
                Curbside
              </Button>
            );
          }
          const isDineIn = value === DINE_IN;
          
          const isDisabled = disabled || (isDineIn && isRestrictedFromTableOrders);
          
          return (
            <Button
              key={value}
              onClick={() => handleOrderTypeSelect(value)}
              variant={selectedOrderType === value && !(value === 'Take Away' && isCurbside) ? 'default' : 'outline'}
              className={cn(
                'h-fit flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap bg-white border transition-colors',
                selectedOrderType === value && !(value === 'Take Away' && isCurbside)
                ? 'text-primary-700 bg-primary-50 border-primary-600 hover:bg-primary-50'
                : 'text-gray-700 border-gray-200 hover:bg-gray-50',
                isDisabled && 'opacity-50 cursor-not-allowed'
              )}
              disabled={isDisabled}
              title={isDineIn && isRestrictedFromTableOrders ? t('errors.dine_in_restricted') || 'Dine In is not available for your role' : undefined}
            >
              <Icon className="w-4 h-4" />
              {t(`order_types.${value.toLowerCase().replace(/ /g, '_')}`)}
            </Button>
          );
        })}
      </div>

      {isCurbside && (
        <div className="mt-2">
          <label htmlFor="pos-car-plate" className="mb-1 block text-sm font-medium text-gray-700">
            Car number plate
          </label>
          <Input
            id="pos-car-plate"
            value={carPlateFrom(orderComment) ?? ''}
            onChange={(e) => {
              const plate = e.target.value.toUpperCase().replace(/[^A-Z0-9 -]/g, '').slice(0, 20);
              setOrderComment(carOrderDraft(plate, carPhoneFrom(orderComment)));
            }}
            placeholder="e.g. A 12345"
            disabled={disabled}
            autoFocus
          />
          <label htmlFor="pos-car-phone" className="mb-1 mt-2 block text-sm font-medium text-gray-700">
            Phone number <span className="font-normal text-gray-400">(optional)</span>
          </label>
          <Input
            id="pos-car-phone"
            type="tel"
            inputMode="tel"
            value={carPhoneFrom(orderComment)}
            onChange={(e) => {
              const phone = e.target.value.replace(/[^0-9+ ]/g, '').slice(0, 16);
              setOrderComment(carOrderDraft(carPlateFrom(orderComment) ?? '', phone));
            }}
            placeholder="e.g. 050 123 4567"
            disabled={disabled}
          />
        </div>
      )}

      {selectedOrderType === DINE_IN && selectedTable && (
        <Button
          onClick={() => setShowTableDialog(true)}
          variant="ghost"
          className="h-fit w-fit gap-x-2 mt-2 text-sm text-primary-600 hover:text-primary-700"
          disabled={disabled}
        >
          <HandPlatter className="w-4 h-4" /> {tableDisplayLabel}
        </Button>
      )}

      {showTableDialog && (
        <TableSelectionDialog onClose={handleTableDialogClose} />
      )}
    </div>
  );
};

export default OrderTypeSelect; 