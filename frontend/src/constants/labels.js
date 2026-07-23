// Centralized Uzbek display labels for status/priority/connectivity codes, so
// the same code isn't translated differently on different pages. Pages with a
// genuinely context-specific wording for a shared code (e.g. Package "completed"
// vs Order "completed") still pass their own `labels` map to <StatusBadge>,
// which overrides this default — see components/ui/Badge.jsx.
export const STATUS_LABELS = {
  completed: "Tugallangan",
  synced: "Sinxronlandi",
  accepted: "Qabul qilindi",
  delivered: "Topshirildi",
  resolved: "Hal qilingan",
  active: "Faol",
  draft: "Yangi",
  approved: "Tasdiqlangan",
  ready_for_packaging: "Qadoqlashga tayyor",
  warehouse: "Omborda",
  in_progress: "Jarayonda",
  in_production: "Jarayonda",
  packaging: "Qadoqlanmoqda",
  pending: "Kutilmoqda",
  syncing: "Sinxronlanmoqda",
  warning: "Ogohlantirish",
  review_required: "Tekshirish talab qilinadi",
  partially_ready: "Qisman tayyor",
  maintenance: "Ta'mirda",
  blocked: "Bloklangan",
  conflict: "Muammoli holat",
  rejected: "Rad etildi",
  failed: "Muvaffaqiyatsiz",
  cancelled: "Bekor qilingan",
  stopped: "To'xtagan",
  broken: "Buzilgan",
  not_required: "Kerak emas",
  inactive: "Nofaol",
  not_connected: "Ulanmagan",
};

export const PRIORITY_LABELS = { low: "Past", normal: "Oddiy", high: "Yuqori", urgent: "Shoshilinch" };

export const CONNECTIVITY_LABELS = { online: "Tarmoqda", offline: "Tarmoqsiz" };
