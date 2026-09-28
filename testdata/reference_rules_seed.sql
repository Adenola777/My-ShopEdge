-- Reference rules seed. Values are external facts, sourced and dated, not policy choices.
-- Load as mse_migrator or a superuser. mse_app holds SELECT only on this table.
--
-- Written by Emergent AI in Adenola777/MYSHOPEDGE (commit 91aeed4) and brought into this
-- repository on 28 September 2026 at the owner's instruction. NOT RE-VERIFIED HERE. Emergent
-- dated its check 26 June 2026, which cannot be right because its work was done on 25
-- September 2026, and that date is what reviewed_at below carries. Check the figure against
-- gov.uk and correct reviewed_at before this is loaded anywhere a seller will read it.
--
-- UK VAT registration threshold: GBP 90,000, effective 1 April 2024, under the Value Added
-- Tax (Increase of Registration Limits) Order 2024.
insert into reference_rules
  (rule_set, rule_key, value, effective_from, source_url, reviewed_by, reviewed_at)
values
  ('vat', 'registration_threshold',
   '{"amount_minor": 9000000, "currency": "GBP"}',
   '2024-04-01',
   'https://www.gov.uk/register-for-vat',
   'HMRC, Value Added Tax (Increase of Registration Limits) Order 2024',
   '2026-06-26')
on conflict (rule_set, rule_key, effective_from) do update set
  value = excluded.value,
  source_url = excluded.source_url,
  reviewed_by = excluded.reviewed_by,
  reviewed_at = excluded.reviewed_at;
