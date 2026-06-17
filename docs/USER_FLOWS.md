# User Flows & Use Cases

## Member Flows

### Flow 1: Sign In & View Personal Menu

```
/start
  ↓
"ورود به حساب کاربری" button
  ↓
Bot: "لطفا نام کاربری خود را وارد کنید"
  ↓
Member: "dan_bosbos"
  ↓
[Backend: user.get_user_by_username → returns user data]
  ↓
Personal Menu:
  ├─ درخواست وام (if LOAN_CREATE permission)
  ├─ شارژ کیف پول
  ├─ پرداخت قسط
  ├─ اطلاعات بانکی
  └─ بازگشت
```

**Key Points:**
- Username stored in `user_data["username"]`
- Roles & permissions fetched from backend on sign in
- User ID (`user_id`) stored in `user_data` for all operations

---

### Flow 2: Apply for Loan (Member)

```
Personal Menu → درخواست وام
  ↓
Bot shows duration buttons:
  ├─ ۶ ماه
  ├─ ۱۲ ماه
  ├─ ۱۵ ماه
  └─ انصراف
  
Member selects "۱۲ ماه"
  ↓
Bot confirms: "درخواست وام | مدت بازپرداخت: ۱۲ ماه | آیا مطمئن هستید?"
  ├─ ✅ تایید و ارسال
  └─ ❌ انصراف
  
Member: ✅ تایید
  ↓
[RPC: loan.create(user_id, duration_months=12, member_chat_id)]
  ↓
Backend response:
  ├─ Success: Loan created, notifies admins
  ├─ Error: "User already has active loan" or "insufficient_balance"
  
Bot: "درخواست شما ثبت شد و در انتظار بررسی است ✅"
  ↓
Admin receives notification → See Admin Flow 1
```

**State Variables:**
- `loan_flow` — tracks state (duration, confirm)
- `loan_duration` — selected duration in months
- `user_id` — from sign-in

**Backend:**
- Checks: active loan exists? balance ≥ threshold?
- Creates Loan(user_id, duration_months, member_chat_id, status=pending)
- Notifies admins via `notify.loan_request`

---

### Flow 3: Charge Wallet (Deposit)

```
Personal Menu → شارژ کیف پول
  ↓
Bot: "لطفا مبلغ واریز را به تومان وارد کنید:"
  ↓
Member: "1000000"
  ↓
Validation:
  ├─ Non-numeric? → Error: "لطفا یک عدد صحیح وارد کنید"
  ├─ Zero/negative? → Error: "لطفا یک عدد مثبت وارد کنید"
  └─ Valid → Proceed
  
Bot: "لطفا فیش یا رسید واریز را ارسال کنید (عکس یا متن):"
  
Member sends:
  ├─ Photo: [photo file_id]
  └─ or Text: "رسید واریز شماره ۱۲۳۴۵۶"
  
[RPC: deposit.create(user_id, amount, proof_type, proof_content)]
  ↓
Backend: Creates DepositRequest(status=pending), notifies admins
  
Bot: "درخواست شارژ ثبت شد ✅ در انتظار تایید ادمین"
  ↓
Admin receives notification → See Admin Flow 2
```

**State Variables:**
- `deposit_flag` — "amount" or "proof"
- `deposit_amount` — numeric amount

**Backend:**
- Creates DepositRequest(user_id, amount, proof_type, proof_content, status=pending)
- Notifies admins via `notify.deposit_request`
- On approval: credits account, writes Transaction(type=deposit, direction=credit)

---

### Flow 4: Pay Installment

```
Personal Menu → پرداخت قسط
  ↓
[RPC: installment_payment.get_pending(user_id)]
  ↓
Backend returns pending installments OR empty list
  
If empty:
  Bot: "قسط معوقی وجود ندارد"
  
If found:
  Buttons for each:
    ├─ "1,000,000 تومان — سررسید 2026-07-17"
    ├─ "1,000,000 تومان — سررسید 2026-08-17"
    └─ ...
  
Member taps installment
  ↓
Bot: "لطفا فیش یا رسید پرداخت را ارسال کنید (عکس یا متن):"
  
Member sends:
  ├─ Photo: [file_id]
  └─ or Text: "واریز قسط شماره۱"
  
[RPC: installment_payment.create(user_id, installment_id, proof_type, proof_content)]
  ↓
Backend: Creates InstallmentPaymentRequest(status=pending), notifies admins
  
Bot: "درخواست پرداخت قسط ثبت شد ✅ در انتظار تایید ادمین"
```

**State Variables:**
- `installment_payment_proof_flag` — installment_id waiting for proof

**Backend:**
- Validates: installment belongs to user & is pending
- Creates InstallmentPaymentRequest(status=pending)
- On approval: sets installment.status=paid, debits account, writes Transaction(type=installment_payment, direction=debit)

---

### Flow 5: Update Bank Info

```
Personal Menu → اطلاعات بانکی
  ↓
├─ مشاهده اطلاعات بانکی → Shows current card/IBAN or "ثبت نشده"
└─ ویرایش اطلاعات بانکی
    ├─ شماره کارت
    │   ├─ Bot: "شماره کارت ۱۶ رقمی خود را وارد کنید:"
    │   ├─ Member: "6037991234567890"
    │   ├─ Validation: Must be exactly 16 digits
    │   └─ [RPC: bank_info.save(user_id, "card_number", value)]
    │
    └─ شماره شبا / IBAN
        ├─ Bot: "شماره شبا / IBAN خود را وارد کنید (مثال: IR...):"
        ├─ Member: "IR062170000000109202965164"
        ├─ Validation: Must match IR + 24 digits (case-insensitive)
        ├─ Auto-uppercase
        └─ [RPC: bank_info.save(user_id, "iban_number", value)]

Bot: "اطلاعات بانکی شما ذخیره شد ✅"
```

**State Variables:**
- `bank_info_flag` — "card_number" or "iban_number"

**Backend:**
- Updates/creates UserBankInfo row for user_id

---

## Admin Flows

### Admin Flow 1: Review & Approve Loan Request

```
Admin receives notification:
  ┌─────────────────────────────────────┐
  │ درخواست وام جدید:                    │
  │ کاربر: Ali Rezaei                    │
  │ مدت بازپرداخت: 12 ماه               │
  │                                       │
  │ [✅ تایید] [❌ رد کردن]              │
  │ [📋 سابقه مشتری]                    │
  └─────────────────────────────────────┘

Admin taps: ✅ تایید
  ↓
Bot: "درخواست وام شماره 42 | لطفا مبلغ وام را به تومان وارد کنید:"
  ↓
Admin: "5000000"
  ↓
[RPC: loan.approve(loan_id=42, requested_by=admin_id, amount=5000000)]
  ↓
Backend:
  ├─ Validates: loan status == pending, balance ≥ amount
  ├─ Creates Loan.amount, monthly_amount, status=approved
  ├─ Debits FundPool
  ├─ Credits member account
  ├─ Writes Transaction(type=loan_disbursement, direction=credit)
  ├─ Generates installments (12 × 416,666)
  └─ Notifies member via notify.loan_approved
  
Bot: "✅ وام شماره 42 با مبلغ 5,000,000 تومان تایید شد"
```

**Alternative: Reject**

```
Admin taps: ❌ رد کردن
  ↓
Bot: "درخواست وام شماره 42 | لطفا دلیل رد کردن وام را وارد کنید:"
  ↓
Admin: "متقاضی یک وام فعال دارد"
  ↓
[RPC: loan.reject(loan_id=42, requested_by=admin_id, rejection_reason=...)]
  ↓
Backend: Sets Loan.status=rejected, rejection_reason
  ↓
Bot notifies member via notify.loan_rejected
  
Bot: "✅ وام رد شد"
```

---

### Admin Flow 2: Review & Approve Deposit

```
Admin receives notification:
  ┌─────────────────────────────────────┐
  │ درخواست شارژ کیف پول جدید:         │
  │ کاربر: Ali Rezaei                    │
  │ مبلغ: 1,000,000 تومان              │
  │ نوع مدرک: عکس                       │
  │ [Photo of receipt]                   │
  │                                       │
  │ [✅ تایید] [❌ رد کردن]              │
  └─────────────────────────────────────┘

Admin taps: ✅ تایید
  ↓
[RPC: deposit.approve(deposit_id=X, requested_by=admin_id)]
  ↓
Backend:
  ├─ Validates: deposit status == pending
  ├─ Credits member account
  ├─ Writes Transaction(type=deposit, direction=credit)
  ├─ Sets deposit.status=approved, approved_by, approved_at
  └─ Returns success
  
Bot: "✅ درخواست شارژ شماره X تایید شد"
```

**Alternative: Reject**

```
Admin taps: ❌ رد کردن
  ↓
Bot: "درخواست شارژ شماره X | لطفا دلیل رد را وارد کنید:"
  ↓
Admin: "فیش ناقص است"
  ↓
[RPC: deposit.reject(deposit_id=X, requested_by=admin_id, rejection_reason=...)]
  ↓
Bot: "✅ رد شد"
```

---

### Admin Flow 3: Review & Approve Installment Payment

```
Admin receives notification:
  ┌─────────────────────────────────────┐
  │ درخواست پرداخت قسط جدید:           │
  │ کاربر: Ali Rezaei                    │
  │ مبلغ: 416,666 تومان                │
  │ سررسید: 2026-07-17                 │
  │ نوع مدرک: متن                       │
  │ متن رسید: واریز قسط شماره۱          │
  │                                       │
  │ [✅ تایید] [❌ رد کردن]              │
  └─────────────────────────────────────┘

Admin taps: ✅ تایید
  ↓
[RPC: installment_payment.approve(installment_payment_id=Y, requested_by=admin_id)]
  ↓
Backend:
  ├─ Validates: request status == pending
  ├─ Sets installment.status=paid, installment.paid_at
  ├─ Debits member account
  ├─ Writes Transaction(type=installment_payment, direction=debit)
  ├─ Sets request.status=approved
  └─ Returns success
  
Bot: "✅ قسط تایید شد"
```

---

## Timeout & Error Handling

**RPC Timeout** (0.2s per call):
- If backend doesn't respond → `response = None`
- Bot shows: "پاسخی دریافت نشد"

**Validation Error:**
- Card number not 16 digits → "شماره کارت باید ۱۶ رقم باشد"
- IBAN not IR + 24 digits → "شماره شبا / IBAN باید با IR شروع شود و ۲۶ کاراکتر باشد"
- Amount not numeric → "لطفا یک عدد صحیح وارد کنید"

**Permission Denied:**
- Non-admin taps loan approve button → Nothing happens (button not shown if no permission)
- Service method checks `@permission(Permissions.LOAN_APPROVE)` before allowing

**Bot Restart:**
- Backend crashes, user gets KeyError
- Error handler catches `isinstance(context.error, KeyError)`
- Sends: "ربات مجددا راه اندازی شده است. لطفا دوباره /start را بزنید"

---

## State Machine Summary

```
User Data Flags by Feature:

AUTHENTICATION:
  flow: "sign_in" | "sign_up" | None
  username: str
  user_id: int
  roles: list[str]
  chat_id: int

LOAN:
  loan_flow: "duration" | "confirm" | None
  loan_duration: int (6, 12, 15)
  loan_amount: None (set by admin)
  loan_approve_flag: int (loan_id) | None
  loan_reject_flag: int (loan_id) | None

DEPOSIT:
  deposit_flag: "amount" | "proof" | None
  deposit_amount: int | None
  deposit_reject_flag: int (deposit_id) | None

BANK_INFO:
  bank_info_flag: "card_number" | "iban_number" | None

INSTALLMENT_PAYMENT:
  installment_payment_proof_flag: int (installment_id) | None
  installment_payment_reject_flag: int (request_id) | None

Other:
  phone_number_create_user_flag: bool | None
  phone_number_join_user_flag: bool | None
  firstname_flag: bool | None
  lastname_flag: bool | None
  role_name_flag: bool | None
  assign_role_flag: bool | None
  user_role_list_flag: bool | None
  delete_user_role_flag: bool | None
```