export function formatPrice(price: number): string {
  return `¥${price.toLocaleString()}`;
}

export function cn(...classes: (string | undefined | false | null)[]): string {
  return classes.filter(Boolean).join(" ");
}
