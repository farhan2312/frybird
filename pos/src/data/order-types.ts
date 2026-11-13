import { Globe, Phone, ShoppingBag, Truck, Utensils } from "lucide-react";

export type OrderType = "Dine In" | "Take Away" | "Delivery" | "Phone In" | "Aggregators";

export type OrderTypes= {
    label: string;
    value: OrderType;
    icon: React.ElementType;
}

export const ORDER_TYPES: OrderTypes[] = [
    {
        label: "Dine In",
        value: "Dine In",
        icon: Utensils
    },
    {
        label: "Take Away",
        value: "Take Away",
        icon: ShoppingBag
    },
    {
        label: "Home Delivery",
        value: "Delivery",
        icon: Truck
    },
    {
        label: "Phone In",
        value: "Phone In",
        icon: Phone
    },
    {
        label: "Aggregators",
        value: "Aggregators",
        icon: Globe
    }
]

export const DINE_IN="Dine In"

// Orders page tabs; the server filters by these keys (ORDER_KINDS in ury/ury_pos/api.py).
export const ORDER_KIND_TABS = [
    { value: "", label: "All" },
    { value: "dine_in", label: "Dine In" },
    { value: "take_away", label: "Take Away" },
    { value: "curbside", label: "Curbside" },
    { value: "delivery", label: "Home Delivery" },
    { value: "apps", label: "Delivery Apps" },
] as const
export type OrderKind = (typeof ORDER_KIND_TABS)[number]["value"]
export const DEFAULT_ORDER_TYPE="Take Away"
// sync_order requires a customer; orders that don't ask for one go to this.
export const WALK_IN_CUSTOMER="Walk-In Customer"
export const DEFAULT_PAYMENT_MODE="Credit Card"
export const COUNTER_PAYMENT_MODES=["Credit Card","Cash"]

export type OrderStatusType = "Draft" | "Recently Paid" | "Paid" | "Consolidated" | "Return";

// Base status types that are always available
export const BASE_ORDER_STATUS_TYPES = [
    {
        label: "Open Orders",
        value: "Draft"
    }
];

// Recently Paid status that appears when paid_limit > 0
export const RECENTLY_PAID_STATUS_TYPE = [
    {
        label: "Recently Paid",
        value: "Recently Paid"
    }
];

// Extended status types that are only available when view_all_status is enabled
export const EXTENDED_ORDER_STATUS_TYPES = [
    {
        label: "Paid",
        value: "Paid"
    },
    {
        label: "Consolidated",
        value: "Consolidated"
    },
    {
        label: "Return",
        value: "Return"
    }
];

// Function to get order status types based on POS profile settings
export const getOrderStatusTypes = (viewAllStatus?: number, paidLimit?: number) => {
    let statusTypes = [...BASE_ORDER_STATUS_TYPES];
    
    // Add Recently Paid if paid_limit > 0
    if (paidLimit && paidLimit > 0) {
        statusTypes.push(...RECENTLY_PAID_STATUS_TYPE);
    }
    
    // Add extended statuses if view_all_status is enabled
    if (viewAllStatus === 1) {
        statusTypes.push(...EXTENDED_ORDER_STATUS_TYPES);
    }
    
    return statusTypes;
};

// Legacy export for backward compatibility
export const ORDER_STATUS_TYPES = BASE_ORDER_STATUS_TYPES;