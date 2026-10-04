# Mock channel APIs (Shopify Admin REST + Amazon SP-API subset)

Run `python3 mock_channels/server.py` (http://127.0.0.1:8770). Treat it as a black box. Use it over HTTP only, and do not read or edit its other files. State persists in mock_channels/state.json.

## Shopify Admin API (header `X-Shopify-Access-Token: shpat_test_northfield`)
Limit: 4 calls per second, after which you get 429 with Retry-After.
- `GET /admin/api/2024-07/products.json?limit=10` paginates with a `Link: <…page_info=…>; rel="next"` header.
- `GET /admin/api/2024-07/locations.json`
- `PUT /admin/api/2024-07/variants/{id}.json` with body `{"variant": {"price": "12.99", "barcode": "…"}}`
- `PUT /admin/api/2024-07/products/{id}.json` with body `{"product": {"status": "active|draft|archived"}}`
- `POST /admin/api/2024-07/inventory_levels/set.json` with body `{"location_id": 7001, "inventory_item_id": …, "available": n}`

## Amazon SP-API (header `x-amz-access-token: Atza|northfield-test`)
- `POST /sp/feeds` with body `{"feedType": "POST_FLAT_FILE_PRICEANDQUANTITYONLY_UPDATE_DATA", "content": "<tab-delimited text>"}` returns 202 `{"feedId": …}`
- `GET /sp/feeds/{feedId}` returns processingStatus IN_QUEUE, then IN_PROGRESS, then DONE (poll until DONE)
- `GET /sp/feeds/{feedId}/report` gives the per-row processing report. Only rows without errors are applied.
- `GET /sp/listings/{sku}` gives the current price, limits and quantity

Feed header row (exact): `sku  price  minimum-seller-allowed-price  maximum-seller-allowed-price  quantity  handling-time  fulfillment-channel` (tab-separated)
