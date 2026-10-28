import { useMemo, useRef, useState } from 'react'
import { formatCurrency } from '@ury/core'
import { useOrderingSession } from '../hooks/useOrderingSession'
import { getProduct, type MenuItem, type OrderingContext } from '../lib/api'

interface LayoutProps {
  initialContext?: OrderingContext
}

function MobileQRLayout({ initialContext }: LayoutProps) {
  const {
    context,
    menu,
    order,
    cart,
    loading,
    submitting,
    error,
    billRequested,
    paymentRequest,
    payingOnline,
    addToCart,
    decrementCart,
    submitCart,
    handleRequestBill,
    payOnline,
    resetSession,
    cartItems,
    cartCount,
    cartTotal,
  } = useOrderingSession(initialContext)
  const [carPlate, setCarPlate] = useState('')

  // Add-ons (extra cheese, spice level...): tapping an item that has add-ons opens a picker first
  const [optionsFor, setOptionsFor] = useState<{ item: MenuItem; addons: MenuItem[] } | null>(null)
  const [chosen, setChosen] = useState<Record<string, boolean>>({})
  const [openingItem, setOpeningItem] = useState<string | null>(null)
  const addonCache = useRef<Record<string, string[]>>({})
  const menuByCode = useMemo(() => Object.fromEntries(menu.map((m) => [m.item, m])), [menu])

  async function handleItemTap(item: MenuItem) {
    if (!context) return
    let codes = addonCache.current[item.item]
    if (!codes) {
      setOpeningItem(item.item)
      try {
        const detail = await getProduct(context.session, item.item)
        codes = detail.addons.map((a) => a.item_code)
      } catch {
        codes = []
      } finally {
        setOpeningItem(null)
      }
      addonCache.current[item.item] = codes
    }
    const addons = codes.map((c) => menuByCode[c]).filter(Boolean) as MenuItem[]
    if (addons.length === 0) {
      addToCart(item)
      return
    }
    setChosen({})
    setOptionsFor({ item, addons })
  }

  function confirmOptions() {
    if (!optionsFor) return
    addToCart(optionsFor.item)
    optionsFor.addons.filter((a) => chosen[a.item]).forEach((a) => addToCart(a))
    setOptionsFor(null)
  }

  function handleStartOver() {
    if (window.confirm('Start over? Your current cart will be cleared.')) {
      resetSession()
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        Loading menu…
      </div>
    )
  }

  if (error && !context) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6 text-center text-destructive">
        {error}
      </div>
    )
  }

  // `source` (not the absence of a table) is the authoritative signal for
  // pickup mode — set server-side by _verify_qr_token/_resolve_device, never
  // guessed from context.table being falsy.
  const isPickup = context?.source === 'QR Pickup'
  // QR pickup is run as curbside: the first order needs the car's number plate
  const needsPlate = isPickup && !order?.invoice
  const plateMissing = needsPlate && carPlate.trim() === ''

  return (
    <div className="min-h-screen pb-28">
      <header className="sticky top-0 z-10 flex items-center justify-between border-b bg-background/95 px-4 py-3 backdrop-blur">
        <h1 className="text-lg font-semibold">
          {isPickup ? 'Curbside Order' : context?.table ? `Table ${context.table}` : 'Order'}
        </h1>
        <button
          onClick={handleStartOver}
          className="rounded-md border px-2 py-1 text-xs font-medium text-muted-foreground"
        >
          Start Over
        </button>
      </header>

      {error && (
        <div className="mx-4 mt-3 rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
      )}

      {order && order.items.length > 0 && (
        <section className="mx-4 mt-4 rounded-lg border p-3">
          <h2 className="mb-2 text-sm font-medium text-muted-foreground">Your order so far</h2>
          {isPickup && order.pickup_code && (
            <p className="mb-2 rounded-md bg-muted p-2 text-center text-sm font-semibold">
              Order {order.pickup_code}
              {order.car_plate && <> &middot; we&apos;ll bring it to car {order.car_plate}</>}
            </p>
          )}
          <ul className="space-y-1 text-sm">
            {order.items.map((row, idx) => (
              <li key={`${row.item_code}-${idx}`} className="flex justify-between">
                <span>{row.item_name} × {row.qty}</span>
                <span>{row.amount}</span>
              </li>
            ))}
          </ul>
          <div className="mt-2 flex justify-between border-t pt-2 text-sm font-semibold">
            <span>Total</span>
            <span>{order.grand_total}</span>
          </div>
          {context?.capabilities.customer_payment_enabled && !order.billed && (
            <button
              className="mt-3 w-full rounded-md bg-primary py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
              disabled={payingOnline}
              onClick={payOnline}
            >
              {payingOnline ? 'Starting payment…' : 'Pay Online'}
            </button>
          )}
          {paymentRequest && !paymentRequest.payment_url && (
            <p className="mt-2 text-xs text-muted-foreground">
              Payment request created ({paymentRequest.amount} {paymentRequest.currency}) — a staff
              member will assist with payment.
            </p>
          )}
          {!isPickup && context?.capabilities.request_bill_enabled && !order.billed && (
            <button
              className="mt-3 w-full rounded-md border py-2 text-sm font-medium disabled:opacity-50"
              disabled={billRequested}
              onClick={handleRequestBill}
            >
              {billRequested ? 'Bill requested — staff notified' : 'Request Bill'}
            </button>
          )}
        </section>
      )}

      <section className="mx-4 mt-4 grid grid-cols-2 gap-3">
        {menu.map((item) => (
          <button
            key={item.item}
            onClick={() => handleItemTap(item)}
            disabled={openingItem === item.item}
            className="flex flex-col overflow-hidden rounded-lg border text-left transition active:scale-[0.98] disabled:opacity-60"
          >
            {context?.capabilities.show_item_images && item.item_image && (
              <img src={item.item_image} alt={item.item_name} className="h-24 w-full object-cover" />
            )}
            <div className="p-2">
              <div className="text-sm font-medium">{item.item_name}</div>
              <div className="text-sm text-muted-foreground tabular-nums">{formatCurrency(item.rate)}</div>
              {cart[item.item] && (
                <div className="mt-1 text-xs font-semibold text-primary">In cart: {cart[item.item].qty}</div>
              )}
            </div>
          </button>
        ))}
      </section>

      {optionsFor && (
        <div className="fixed inset-0 z-20 flex items-end bg-black/40" onClick={() => setOptionsFor(null)}>
          <div className="w-full rounded-t-2xl bg-background p-4" onClick={(e) => e.stopPropagation()}>
            <div className="mb-1 text-base font-semibold">{optionsFor.item.item_name}</div>
            <div className="mb-3 text-sm text-muted-foreground">Choose add-ons (optional)</div>
            <ul className="mb-4 space-y-2">
              {optionsFor.addons.map((a) => (
                <li key={a.item}>
                  <label className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                    <span className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={!!chosen[a.item]}
                        onChange={(e) => setChosen((prev) => ({ ...prev, [a.item]: e.target.checked }))}
                        className="h-4 w-4"
                      />
                      {a.item_name}
                    </span>
                    <span className="tabular-nums text-muted-foreground">
                      {a.rate ? `+${formatCurrency(a.rate)}` : 'Free'}
                    </span>
                  </label>
                </li>
              ))}
            </ul>
            <div className="flex gap-2">
              <button onClick={() => setOptionsFor(null)} className="flex-1 rounded-md border py-3 text-sm font-medium">
                Cancel
              </button>
              <button
                onClick={confirmOptions}
                className="flex-[2] rounded-md bg-primary py-3 text-sm font-medium text-primary-foreground"
              >
                Add to cart
              </button>
            </div>
          </div>
        </div>
      )}

      {cartCount > 0 && (
        <div className="fixed inset-x-0 bottom-0 border-t bg-background p-4">
          <ul className="mb-2 max-h-32 space-y-1 overflow-y-auto text-sm">
            {cartItems.map((entry) => (
              <li key={entry.item.item} className="flex items-center justify-between">
                <span>{entry.item.item_name}</span>
                <span className="flex items-center gap-2">
                  <button
                    onClick={() => decrementCart(entry.item.item)}
                    className="h-6 w-6 rounded-full border text-xs leading-none"
                    aria-label={`Remove one ${entry.item.item_name}`}
                  >
                    −
                  </button>
                  {entry.qty}
                  <button
                    onClick={() => addToCart(entry.item)}
                    className="h-6 w-6 rounded-full border text-xs leading-none"
                    aria-label={`Add one more ${entry.item.item_name}`}
                  >
                    +
                  </button>
                </span>
              </li>
            ))}
          </ul>
          <div className="mb-2 flex items-center justify-between text-sm font-semibold">
            <span>{cartCount} item{cartCount > 1 ? 's' : ''}</span>
            <span className="tabular-nums">{formatCurrency(cartTotal)}</span>
          </div>
          {needsPlate && (
            <label className="mb-2 block text-sm">
              <span className="mb-1 block font-medium">Car number plate</span>
              <input
                value={carPlate}
                onChange={(e) => setCarPlate(e.target.value.toUpperCase())}
                placeholder="e.g. AJMAN B 12345"
                maxLength={20}
                autoCapitalize="characters"
                className="w-full rounded-md border px-3 py-2 uppercase tracking-wide"
              />
              <span className="mt-1 block text-xs text-muted-foreground">
                We&apos;ll bring your order out to your car.
              </span>
            </label>
          )}
          <button
            onClick={() => submitCart(isPickup ? carPlate : undefined)}
            disabled={submitting || plateMissing}
            className="w-full rounded-md bg-primary py-3 font-medium text-primary-foreground disabled:opacity-50"
          >
            {submitting ? 'Placing order…' : plateMissing ? 'Enter your car number plate' : 'Place Order'}
          </button>
        </div>
      )}
    </div>
  )
}

export default MobileQRLayout
