# A32. What TikTok's Inventory Search returns, and how stock is read

Written 30 September 2026. The owner asked that stock follow what sells and what comes back.
The daily sync did not read stock at all, so no real shop had a stock record and a checked
return changed no count. This records the facts the stock read is built on.

## 32.1 The facts, and where each came from

| Fact | Source |
|---|---|
| Path `/product/202309/inventory/search`, scope `seller.product.basic` | TikTok's Inventory Search page, pasted by the owner on 30 September |
| Body `product_ids`, at most 100, or `sku_ids`, at most 600. SKU IDs win when both are sent | The same page |
| Both connected shops hold `seller.product.basic` | `tiktok_connections.scopes` on production, queried 30 September |
| The method is POST | The live call from the Render cron job at 08:38 UTC, which TikTok answered with code 0 |
| `data.inventory[]` holds `product_id` and `skus[]`. Each SKU holds `id`, `seller_sku`, `total_available_quantity`, `total_committed_quantity`, `total_available_inventory_distribution.in_shop_inventory.quantity` and `warehouse_inventory[]` with `available_quantity`, `committed_quantity` and `warehouse_id` | The same live call, for My Special Mug in My ShopEdge. It is kept verbatim at `testdata/live/inventory_search_my_shopedge_30_september.json` |

The page as pasted did not show the method or what `data` holds. Both were learnt from the
live call rather than assumed, which is why a read-only probe ran first.

## 32.2 How the sync uses it

- Stock is read after orders, returns and statements, as a fourth domain, `inventory`, in
  `sync_runs`.
- Every product MyShopEdge has read from an order is asked about, a hundred at a time.
- `tiktok_stock` takes `total_available_quantity`. TikTok lowers that figure itself when an
  item sells, so On the shelf falls with each sale at the next sync.
- A variant with no stock record gets one. An existing record goes through STK-8 (A4.1)
  before its count is replaced:
  - a rise in TikTok's count is absorbed into the seller's adjustment, up to the size of the
    adjustment, with an `adjustment_absorbed` movement and one notice per variant per day;
  - a rise above the seller's tolerance, 20 units unless they changed it, flows through and
    raises a discrepancy instead;
  - a fall is never absorbed.
- A checked return now finds the variant's stock record, so a resellable unit goes back on the
  shelf and an unsellable one is written off, as A30.2 rules.

## 32.3 What is still unverified or not built

- **`total_committed_quantity` is stored as `sold_not_posted`.** The field's name suggests
  units reserved for orders not yet dispatched, but the only real answer carried 0, with no
  open order to test it against.
- **Only variants that have sold are read.** A product never ordered is unknown to
  MyShopEdge, because the product listing that would name it has not been called.
- **Nothing explains a rise.** A4's step 1 subtracts a rise explained by a recorded movement,
  such as a cancellation restoring stock. The sync writes no sale, dispatch or cancellation
  movements yet, so every rise counts as unexplained. The count stays right, because it is
  TikTok's own, but S26's movement history does not yet list sales.
- **Coming back is not counted.** Nothing raises `coming_back` when a return is opened.
- **A product with several variants still shows no count on its product screen**, because
  the contract carries one stock position per product (A25).

## 32.4 Checked

`testdata/tiktok_sync_check.py` passed 45 of 45 on both datasets on 30 September. Its fake
TikTok answers in the live shape, and one check fails if that shape drifts from the recorded
answer. TC-STK-08, 09, 10 and 11 run against real rows.
