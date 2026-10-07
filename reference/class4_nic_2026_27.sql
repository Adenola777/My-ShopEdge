-- Class 4 National Insurance for the 2026 to 2027 tax year, for the sole-trader set-aside
-- (A30.3).
--
-- Read on 7 October 2026 from HMRC's guidance "Rates and allowances: National Insurance
-- contributions", updated 6 April 2026, section 3.2 Class 4, as the owner pasted it into the
-- session. The paste carried the page's title and breadcrumbs but not its address. The
-- source_url below is the HMRC publication of that title and should be confirmed by opening
-- it before the row is marked reviewed.
--
-- What the page gives for 2026 to 2027:
--   Lower Profits Limit 12,570. Upper Profits Limit 50,270.
--   Rate between the two limits 6%. Rate above the Upper Profits Limit 2%.
-- The same page lists Class 2 (Small Profits Threshold 7,105, 3.65 a week). The set-aside
-- does not model Class 2 (tax.py, _estimate), so it is not recorded here.
--
-- NOT LOADED, and reviewed_at is null, so the service ignores the row until the owner
-- approves the figures. Load as mse_migrator.
insert into reference_rules
  (rule_set, rule_key, value, effective_from, effective_to, source_url, reviewed_by, reviewed_at)
values
  ('national_insurance', 'class4_nic',
   '{"lower_minor": 1257000, "upper_minor": 5027000, "main_rate_bp": 600, "upper_rate_bp": 200}',
   '2026-04-06', '2027-04-05',
   'https://www.gov.uk/government/publications/rates-and-allowances-national-insurance-contributions',
   null, null)
on conflict (rule_set, rule_key, effective_from) do update set
  value = excluded.value, effective_to = excluded.effective_to, source_url = excluded.source_url;
