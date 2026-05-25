# Sierra Outfitters Eval Summary — 2026-05-25

**24/24 tests passed**


## ✅ Auth — 100% (4/4 tests)

`██████████`

- ✅ [test_no_email_no_order_data](auth/test_no_email_no_order_data.md)
- ✅ [test_cannot_view_other_customers_order](auth/test_cannot_view_other_customers_order.md)
- ✅ [test_correct_owner_can_view_order](auth/test_correct_owner_can_view_order.md)
- ✅ [test_new_customer_registered_with_first_and_last_name](auth/test_new_customer_registered_with_first_and_last_name.md)

## ✅ Order Lookup — 100% (4/4 tests)

`██████████`

- ✅ [test_agent_asks_for_email_first](order_lookup/test_agent_asks_for_email_first.md)
- ✅ [test_lists_orders_by_email](order_lookup/test_lists_orders_by_email.md)
- ✅ [test_tracking_url_surfaced](order_lookup/test_tracking_url_surfaced.md)
- ✅ [test_unknown_order_id_gracefully_handled](order_lookup/test_unknown_order_id_gracefully_handled.md)

## ✅ Order Placement — 100% (5/5 tests)

`██████████`

- ✅ [test_out_of_stock_rejected](order_placement/test_out_of_stock_rejected.md)
- ✅ [test_agent_confirms_before_placing](order_placement/test_agent_confirms_before_placing.md)
- ✅ [test_order_stores_valid_promo_code](order_placement/test_order_stores_valid_promo_code.md)
- ✅ [test_order_rejects_other_customers_promo_code](order_placement/test_order_rejects_other_customers_promo_code.md)
- ✅ [test_claim_then_use_promo_code_on_order](order_placement/test_claim_then_use_promo_code_on_order.md)

## ✅ Product Search — 100% (4/4 tests)

`██████████`

- ✅ [test_search_by_activity_tag](product_search/test_search_by_activity_tag.md)
- ✅ [test_out_of_stock_excluded_from_results](product_search/test_out_of_stock_excluded_from_results.md)
- ✅ [test_browse_all_products](product_search/test_browse_all_products.md)
- ✅ [test_no_match_gracefully_handled](product_search/test_no_match_gracefully_handled.md)

## ✅ Promotion Claims — 100% (4/4 tests)

`██████████`

- ✅ [test_claim_within_window_succeeds](promotion_claims/test_claim_within_window_succeeds.md)
- ✅ [test_claim_generates_and_surfaces_code](promotion_claims/test_claim_generates_and_surfaces_code.md)
- ✅ [test_claim_idempotent](promotion_claims/test_claim_idempotent.md)
- ✅ [test_claim_outside_window_error_relayed](promotion_claims/test_claim_outside_window_error_relayed.md)

## ✅ Promotions — 100% (3/3 tests)

`██████████`

- ✅ [test_greets_and_surfaces_active_promo](promotions/test_greets_and_surfaces_active_promo.md)
- ✅ [test_expired_promo_not_surfaced](promotions/test_expired_promo_not_surfaced.md)
- ✅ [test_no_active_promos_no_hallucination](promotions/test_no_active_promos_no_hallucination.md)
