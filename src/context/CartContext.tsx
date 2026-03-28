"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import { Product } from "@/data/products";

export interface CartItem {
  product: Product;
  quantity: number;
  selectedSize?: string;
  unitPrice: number;
}

interface CartContextType {
  items: CartItem[];
  addItem: (product: Product, size?: string) => void;
  removeItem: (productId: string, size?: string) => void;
  updateQuantity: (productId: string, quantity: number, size?: string) => void;
  clearCart: () => void;
  totalItems: number;
  totalPrice: number;
  isCartOpen: boolean;
  setIsCartOpen: (open: boolean) => void;
}

const CartContext = createContext<CartContextType | undefined>(undefined);

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([]);
  const [isCartOpen, setIsCartOpen] = useState(false);

  const getItemKey = (productId: string, size?: string) =>
    size ? `${productId}-${size}` : productId;

  const addItem = useCallback((product: Product, size?: string) => {
    setItems((prev) => {
      const key = getItemKey(product.id, size);
      const existing = prev.find(
        (item) => getItemKey(item.product.id, item.selectedSize) === key
      );

      const unitPrice = size && product.sizes
        ? product.sizes.find((s) => s.name === size)?.price ?? product.price
        : product.price;

      if (existing) {
        return prev.map((item) =>
          getItemKey(item.product.id, item.selectedSize) === key
            ? { ...item, quantity: item.quantity + 1 }
            : item
        );
      }

      return [...prev, { product, quantity: 1, selectedSize: size, unitPrice }];
    });
    setIsCartOpen(true);
  }, []);

  const removeItem = useCallback((productId: string, size?: string) => {
    setItems((prev) =>
      prev.filter(
        (item) =>
          getItemKey(item.product.id, item.selectedSize) !==
          getItemKey(productId, size)
      )
    );
  }, []);

  const updateQuantity = useCallback(
    (productId: string, quantity: number, size?: string) => {
      if (quantity <= 0) {
        removeItem(productId, size);
        return;
      }
      setItems((prev) =>
        prev.map((item) =>
          getItemKey(item.product.id, item.selectedSize) ===
          getItemKey(productId, size)
            ? { ...item, quantity }
            : item
        )
      );
    },
    [removeItem]
  );

  const clearCart = useCallback(() => setItems([]), []);

  const totalItems = items.reduce((sum, item) => sum + item.quantity, 0);
  const totalPrice = items.reduce(
    (sum, item) => sum + item.unitPrice * item.quantity,
    0
  );

  return (
    <CartContext.Provider
      value={{
        items,
        addItem,
        removeItem,
        updateQuantity,
        clearCart,
        totalItems,
        totalPrice,
        isCartOpen,
        setIsCartOpen,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const context = useContext(CartContext);
  if (!context) throw new Error("useCart must be used within CartProvider");
  return context;
}
