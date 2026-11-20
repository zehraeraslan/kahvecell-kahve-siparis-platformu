export const ORDER_STATUS_LABELS = {
  PENDING: 'Bekliyor',
  ACCEPTED: 'Kabul Edildi',
  PREPARING: 'Hazırlanıyor',
  READY: 'Hazır',
  DELIVERED: 'Teslim Edildi',
}

export function getOrderStatusLabel(status) {
  return ORDER_STATUS_LABELS[status] || status
}
