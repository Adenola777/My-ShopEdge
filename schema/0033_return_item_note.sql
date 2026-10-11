-- 0033. The seller's optional note on a return check. Written 11 October 2026, A36 item 4.
--
-- **NOT YET APPLIED to any Neon branch.** Applied on 11 October 2026 to local PostgreSQL 16
-- databases only. See A36.12 for what was checked.
--
-- WHAT THE BRIEF ASKS FOR
--
-- Section 14 of the owner's brief lists "Optional note" in the return detail, beside the
-- Resellable and Unsellable actions. The owner approved building it on 11 October 2026.
--
-- THE COLUMN, `return_items.seller_note`
--
-- The note is written with the check, in the same request, and a check is one way
-- (checkReturnItem answers 409 on a second check), so the note is never edited afterwards.
-- It is null when the seller wrote nothing.
--
-- **Derived, not ruled:** at most 500 characters. The brief sets no length. 500 is room for a
-- few sentences about the state of an item, and a bound keeps one row from carrying a document.
-- The service refuses a longer note with a reason before it reaches this check.
--
-- Row level security on `return_items` covers the new column, because its policy is on the
-- row. `mse_app` already holds UPDATE on the table, and a table grant covers a column added
-- later. Adding a nullable column with no default rewrites no row.

alter table return_items
  add column seller_note text
    check (seller_note is null or char_length(seller_note) between 1 and 500);

comment on column return_items.seller_note is
  'The seller''s optional note, written with the check (A36 item 4). Null when none was written.';
