# ✅ test_new_customer_registered_with_first_and_last_name

**Domain:** Auth  
**Date:** 2026-05-25

---

## What this test checks

> A brand-new email triggers the registration flow.  The agent must explicitly
> ask for first and last name, then call register_customer with the full name,
> and the DB must store it correctly.

> PASS criteria
> -------------
> - lookup_customer called with the new email and returns known_customer=False.
> - The agent's reply asks for both first and last name.
> - register_customer called with customer_name == 'Jane Smith'.
> - The customers table contains a row with name 'Jane Smith' and the new email.

## Outcome

**PASSED** — all assertions met.

## Conversation

> **User:** My email is jane.smith.newuser@test.com

**🔧 `lookup_customer`**

**Args:**
```json
{
  "customer_email": "jane.smith.newuser@test.com"
}
```

**Result:**
```json
{
  "known_customer": false,
  "email": "jane.smith.newuser@test.com"
}
```

> **Sierra Outfitters:** Onward into the unknown! It looks like there's no account with the email address "jane.smith.newuser@test.com".

To chart your course with us, could you please provide your first and last name? 🌟

> **User:** My name is Jane Smith

**🔧 `register_customer`**

**Args:**
```json
{
  "customer_email": "jane.smith.newuser@test.com",
  "customer_name": "Jane Smith"
}
```

**Result:**
```json
{
  "registered": true,
  "customer_id": "USR-011",
  "name": "Jane Smith",
  "email": "jane.smith.newuser@test.com"
}
```

> **Sierra Outfitters:** Base camp confirmed, Jane Smith! Welcome to Sierra Outfitters. 🏕️ As a new adventurer with us, keep in mind we currently have a Trail Blazer Sale running. Use code TRAIL20 for 20% off on your next expedition gear. 

If there's anything specific you need for your upcoming journey, just let me know! 🌲🧭
