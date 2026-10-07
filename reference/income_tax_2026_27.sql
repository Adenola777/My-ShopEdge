-- Income Tax rules for the 2026 to 2027 tax year, for the sole-trader set-aside (A30.3).
--
-- Read on 7 October 2026 from HMRC's page "Income Tax rates and allowances for current and
-- previous tax years", updated 6 April 2026, as the owner pasted it into the session. The
-- session cannot reach gov.uk itself, so the text is the owner's copy of that page.
--
-- NOT LOADED, and reviewed_at is null, so the service ignores both rows until the owner
-- approves the figures. Load as mse_migrator, which is the only role that may write
-- reference_rules (0001, 0024).
--
-- What the page gives, England, Northern Ireland and Wales, 2026 to 2027:
--   Personal Allowance 12,570. It goes down by 1 for every 2 of income above 100,000.
--   Basic rate 20% up to 37,700 of income after allowances.
--   Higher rate 40% from 37,701 to 125,140, a band 87,440 wide.
--   Additional rate 45% over 125,140.
-- The starting rate for savings is left out: it applies to savings income, not trading
-- profit. The Scottish bands differ and are not loaded, because the set-aside reads one
-- set of bands and does not know where a seller pays tax. A Scottish taxpayer's estimate
-- would be wrong until that is built.
insert into reference_rules
  (rule_set, rule_key, value, effective_from, effective_to, source_url, reviewed_by, reviewed_at)
values
  ('income_tax', 'income_tax_personal_allowance',
   '{"amount_minor": 1257000, "taper_from_minor": 10000000, "taper_ratio": 2}',
   '2026-04-06', '2027-04-05',
   'https://www.gov.uk/government/publications/rates-and-allowances-income-tax',
   null, null),
  ('income_tax', 'income_tax_bands',
   '{"bands": [{"width_minor": 3770000, "rate_bp": 2000}, {"width_minor": 8744000, "rate_bp": 4000}, {"width_minor": null, "rate_bp": 4500}]}',
   '2026-04-06', '2027-04-05',
   'https://www.gov.uk/government/publications/rates-and-allowances-income-tax',
   null, null)
on conflict (rule_set, rule_key, effective_from) do update set
  value = excluded.value, effective_to = excluded.effective_to, source_url = excluded.source_url;
