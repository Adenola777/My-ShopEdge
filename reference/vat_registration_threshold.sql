-- The VAT registration threshold, for the VAT monitor on S12 (getVatMonitor, TAX-1).
--
-- Read on 7 October 2026 from the gov.uk guide "How VAT works", section "VAT thresholds",
-- as the owner pasted it into the session. The session cannot reach gov.uk itself, so the
-- text is the owner's copy of that page. It reads: "Total taxable turnover. More than
-- £90,000. Register for VAT." The deregistration threshold on the same page, less than
-- £88,000, is not loaded, because nothing in the service reads it.
--
-- The page gives no date from which £90,000 applies. effective_from is therefore the day
-- the page was read, not the day the threshold began, and the monitor reads the threshold
-- in force today. A check of an earlier year needs the historical thresholds page.
--
-- NOT LOADED. Load as mse_migrator with reviewed_by and reviewed_at set, once the owner
-- has approved the figure.
insert into reference_rules
  (rule_set, rule_key, value, effective_from, effective_to, source_url, reviewed_by, reviewed_at)
values
  ('vat', 'registration_threshold',
   '{"amount_minor": 9000000, "currency": "GBP"}',
   '2026-10-07', null,
   'https://www.gov.uk/how-vat-works/vat-thresholds',
   null, null)
on conflict (rule_set, rule_key, effective_from) do update set
  value = excluded.value, effective_to = excluded.effective_to, source_url = excluded.source_url;
