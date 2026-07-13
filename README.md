# SPP — Silknode Production Platform

Mebel ishlab chiqarish korxonasi uchun buyurtma, ishlab chiqarish, qadoqlash va ombor jarayonlarini boshqarish platformasi. Tizim admin panel (buyurtmalar, hisobotlar, foydalanuvchilar) va sex/terminal interfeysidan (ishlab chiqarish bosqichlarini QR orqali belgilash) iborat.

## Stack

- **Backend:** Django + Django REST Framework, JWT autentifikatsiya (`simplejwt`), PostgreSQL
- **Frontend:** React (Vite), Tailwind CSS, Zustand, PWA (offline-ready terminal)

## Loyiha tuzilishi

```
backend/
  accounts/       — foydalanuvchilar va autentifikatsiya
  manufacturing/  — ishlab chiqarish jarayonlari
  orders/         — buyurtmalar
  packaging/      — qadoqlash
  warehouse/      — ombor
  terminalapp/    — sex terminali API
  core/           — umumiy komponentlar, dashboard, hisobotlar
frontend/
  src/            — React ilova (admin panel + terminal)
```

## Ishga tushirish

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # kerak bo'lsa qiymatlarni moslang
python manage.py migrate
python manage.py runserver
```

PostgreSQL talab qilinadi — `.env` dagi `DATABASE_URL` orqali ulanish manzili sozlanadi.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # kerak bo'lsa qiymatlarni moslang
npm run dev
```

Dev server `http://localhost:5173` da ishga tushadi, `/api` so'rovlari `.env` dagi `VITE_DEV_PROXY_TARGET` orqali backendga proksi qilinadi.
