"""Builds site/faq/tiktok-shop-seller-finance.html from the questions below.

    python3 scripts/site/build_faq.py

Written 10 October 2026 from the owner's "TikTok Shop Seller Finance FAQ". The page and its
FAQPage JSON-LD are generated from one list, so the visible answers and the structured data
cannot drift apart, which the brief requires.

What was changed from the brief, and why. Every claim about MyShopEdge was checked against
the service on 10 October 2026, and an answer says what the product does rather than what it
"should" do. In particular: cost coverage is shown by units sold, not by sales value; the
product shows gross profit and no gross margin yet; payouts carry TikTok's payment status
rather than the five reconciliation labels the brief lists; and ending a plan does not move
an account to a read-only state. TikTok's settlement periods, its 9% commission and its bank
timings are left out, because no TikTok page could be opened from the build session to check
them; the answers send the seller to Seller Center instead. The three gov.uk addresses are
the ones recorded in reference/*.sql, which were opened when the tax figures were loaded.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

APP = "https://app.myshopedge.inspirecraftglobal.com"
START = f"{APP}/start"
EXPLAINER = "/tools/tiktok-shop-payout-explainer"
REVIEWED = "10 October 2026"
NEXT_REVIEW = "10 January 2027"

# (anchor, question, answer html, call to action html or None)
QA: list[tuple[str, str, str, str | None]] = [
    ("why-payout-lower-than-sales", "Why is my TikTok Shop payout lower than my sales?",
     """<p>A sale is not the same as a settlement or a bank payment. Between a customer's order and the money reaching your bank, TikTok Shop can apply seller discounts, platform commission, affiliate commission, shipping charges, promotion fees, refunds, return adjustments and reserves. Some orders may also still be awaiting settlement.</p>
<pre class="calc">Gross sales                       £62.00
Seller discounts                  −£2.00
Platform commission               −£5.40
Affiliate commission              −£3.10
Shipping fee                      −£2.75
Partial refund, weeks later       −£8.00
Paid out                          £40.75</pre>
<p>A lower payout does not by itself mean that money is missing. Check whether the orders are settled, whether refunds or adjustments were posted, which charges were deducted, whether the payout covers more than one statement, and whether the bank payment is still processing.</p>
<p>MyShopEdge puts sales, each named deduction, statements and payouts into one view, so you can follow what changed between a sale and the money received.</p>""",
     f'<p>Work through your own figures with the <a href="{EXPLAINER}">Payout Explainer</a>. It is free, and nothing you type leaves your browser.</p>'),
    ("sales-settlement-payout", "What is the difference between TikTok Shop sales, settlement and payout?",
     """<p><strong>Sales</strong> are the orders customers place in your shop. <strong>Settlement</strong> is the amount TikTok Shop works out after applying discounts, refunds, shipping charges, fees and adjustments. A <strong>payout</strong> is the payment TikTok Shop sends to your bank once the settlement conditions are met.</p>
<pre class="calc">Customer order
  → sale recorded
  → fees, refunds and adjustments applied
  → statement settled
  → payout initiated
  → money credited by your bank</pre>
<p>These happen on different dates, and one payout can cover more than one statement. A sales figure, a settlement total and a bank payment do not have to match on the same day.</p>""", None),
    ("when-does-tiktok-shop-pay", "When does TikTok Shop pay sellers in the UK?",
     """<p>Payment timing depends on the settlement period TikTok Shop sets for your account and for each order. The period normally starts after delivery, and TikTok Shop can lengthen it in some circumstances, for example during a security review. Your bank may take a few working days to credit a payout after TikTok Shop sends it.</p>
<p>Seller Center shows the settlement status of each order and statement, and TikTok's own guidance there sets out the current periods. MyShopEdge shows which statements have been paid and which are still to come.</p>""", None),
    ("tiktok-shop-fees-uk", "What fees does TikTok Shop take from UK sellers?",
     """<p>TikTok Shop deductions can include:</p>
<ul><li>platform commission;</li><li>affiliate or creator commission;</li><li>shipping or fulfilment charges;</li><li>seller-funded discounts;</li><li>promotion fees;</li><li>refund adjustments;</li><li>other charges and adjustments shown in your transaction records.</li></ul>
<p>TikTok Shop publishes its commission policy in Seller Center, and the rate can vary with category, seller programme and policy changes. Your real deductions also depend on your products, promotions, affiliate settings, fulfilment and refunds, so a published rate is a starting point rather than an answer.</p>
<p>MyShopEdge shows the deductions TikTok Shop actually made, each on its own line under TikTok's name for it, rather than estimating them from a percentage.</p>""", None),
    ("calculate-tiktok-shop-profit", "How do I calculate TikTok Shop profit?",
     """<p>Start with what remains after TikTok Shop's deductions, then take away what your products cost.</p>
<pre class="calc">Gross sales
− seller discounts
− refunds
− platform commission
− affiliate commission
− shipping, fulfilment and other deductions
= net proceeds
− product costs
= gross profit</pre>
<p>Gross margin is gross profit divided by net sales, multiplied by 100. Revenue is not profit: product cost, returns, unsellable stock, packaging, advertising, staff, storage, software and other overheads all affect what your business keeps.</p>
<p>MyShopEdge works in two stages. It shows net proceeds before any product costs are added, and it shows gross profit once costs are added. A missing cost is never treated as zero.</p>""",
     f'<p>Start with net proceeds today and <a href="{START}">add product costs</a> whenever you are ready.</p>'),
    ("is-revenue-profit", "Is TikTok Shop revenue the same as profit?",
     """<p>No. Gross sales show what customers paid before deductions. Your payout shows what remains after TikTok Shop has applied fees, refunds and adjustments. Neither figure tells you your product profit, because neither includes what your products cost.</p>
<div class="table-wrap"><table>
<thead><tr><th>Figure</th><th>Meaning</th></tr></thead>
<tbody>
<tr><td>Gross sales</td><td>Customer order value before seller discounts and refunds</td></tr>
<tr><td>Net sales</td><td>Gross sales after seller discounts</td></tr>
<tr><td>Net proceeds</td><td>What remains after TikTok Shop's deductions and refunds, before product costs</td></tr>
<tr><td>Gross profit</td><td>What remains after product costs as well</td></tr>
<tr><td>Gross margin</td><td>Gross profit as a percentage of net sales</td></tr>
</tbody></table></div>""", None),
    ("payout-pending", "Why is my TikTok Shop payout still pending?",
     """<p>A payout can stay pending because the orders are still inside their settlement period, because the statement is not yet settled, because the bank has not finished processing a payment TikTok Shop has sent, because a reserve, hold or adjustment affects it, or because it depends on several statements with different statuses.</p>
<p>Check the delivery date, the settlement and statement status in Seller Center, the payout details, and whether the bank's processing time has passed. Most pending payouts are a matter of timing rather than a fault.</p>""", None),
    ("awaiting-settlement", "What does “awaiting settlement” mean on TikTok Shop?",
     """<p>It means the order exists but TikTok Shop has not yet released it for settlement. This is usually a timing status, not a missing payment. The waiting period normally begins after delivery, and its length depends on your account's settlement terms. An order awaiting settlement can appear in your sales before it appears in a payout.</p>""", None),
    ("refunds-and-returns", "How do refunds and returns affect my payout and profit?",
     """<p>A refund can reduce net proceeds and the payout, can arrive as an adjustment weeks after the sale, and can change how fees are treated on that order.</p>
<p>A return also creates a stock decision. A <strong>resellable</strong> item goes back into stock. An <strong>unsellable</strong> item is written off, so you can lose both the sale and the product's cost. Without the product's cost, the full effect on gross profit cannot be worked out.</p>
<p>In MyShopEdge you mark each return resellable or unsellable, so stock, write-offs and product profit stay accurate.</p>""", None),
    ("net-proceeds", "What is net proceeds?",
     """<p>Net proceeds are what remains after TikTok Shop's deductions and refunds, before your product costs.</p>
<pre class="calc">Gross sales
− seller discounts
− TikTok Shop deductions
− refunds
= net proceeds</pre>
<p>Net proceeds are useful because they tell you what TikTok Shop has left you even before you know what your products cost. They are not gross profit, net profit or taxable profit.</p>""", None),
    ("gross-profit-and-margin", "What is gross profit and gross margin on TikTok Shop?",
     """<p>Gross profit is what remains after TikTok Shop's deductions and your product costs.</p>
<pre class="calc">Net proceeds − product costs = gross profit
Gross profit ÷ net sales × 100 = gross margin</pre>
<p>Gross margin lets you compare products with different prices. A product can sell more than another and still earn less of each pound once its cost, fees and returns are counted.</p>
<p>MyShopEdge shows gross profit, by period and by product, once costs are added. It does not show gross margin yet.</p>""",
     f'<p>See gross profit for your own products: <a href="{START}">add product costs</a>.</p>'),
    ("do-i-need-product-costs", "Do I need to upload product costs to use MyShopEdge?",
     """<p>No. Without costs, MyShopEdge shows your sales, fees, refunds, statements, payouts and net proceeds. Add costs when you want gross profit, profit by product, and the effect of returns and write-offs on profit. You can add costs at any time, by Excel or CSV file or by typing them in.</p>""", None),
    ("cost-coverage", "What is cost coverage?",
     """<p>Cost coverage shows how much of what you sold has a product cost. MyShopEdge measures it in units, for example “212 of 228 units sold in the last 30 days have a cost (93%)”.</p>
<p>It matters because a profit figure built on some costs and not others can look complete when it is not. When a cost is missing, MyShopEdge says so and leaves the profit figure incomplete rather than treating the missing cost as zero.</p>""", None),
    ("add-product-costs", "How do I add product costs to TikTok Shop sales?",
     """<p>In MyShopEdge you can upload an Excel or CSV file, or type costs in product by product. A cost file works best with the seller SKU, the product name, the variant, the cost per unit and, if needed, the date the cost applies from.</p>
<p>Before anything is saved, MyShopEdge shows every row of your file as matched, unmatched or duplicate, with the reason for each row it could not match. You confirm the matched rows, and nothing is assigned to a product silently.</p>""", None),
    ("cost-not-matched", "Why is a product cost missing or not matched?",
     """<p>A row can fail to match when the SKU is missing or differs from TikTok Shop's, when the product has variants the file does not name, when the file holds duplicate rows, or when the cost is blank or not a number.</p>
<p>MyShopEdge keeps those rows visible as unmatched or duplicate, with the reason, rather than guessing or treating the cost as zero. Fix the file and upload it again, or type the cost in.</p>""", None),
    ("profit-by-product", "Can I see TikTok Shop profit by product?",
     """<p>Yes, once the products' costs are added. For each product MyShopEdge shows units sold, net proceeds, returns, and gross profit after returns, and it says when a product's cost is missing.</p>
<p>Products are ranked by gross profit after returns. Where costs are missing, you still see net proceeds and the product's cost status.</p>""", None),
    ("reconcile-payouts", "How do I reconcile TikTok Shop payouts?",
     """<p>Compare the payment received with the settlement statements behind it, and the statements with the transactions behind them.</p>
<pre class="calc">Payout received
  → settlement statements
  → orders included
  → sales, fees, refunds and adjustments
  → difference explained</pre>
<p>Check the payout amount and date, the statement amounts, the orders in each statement, the deductions, refunds and later adjustments, any reserve activity, and the bank's processing time.</p>
<p>In MyShopEdge, Payouts lists each statement with TikTok Shop's payment status, the money behind it line by line, and whether its lines add up to what TikTok paid.</p>""",
     f'<p>Reconcile your own payouts and build a file your accountant can use: <a href="{START}">start your free 30-day trial</a>.</p>'),
    ("settlement-statement", "What is a TikTok Shop settlement statement?",
     """<p>A settlement statement is TikTok Shop's record of the activity that makes up a settlement amount: orders, refunds, fees, shipping charges and adjustments. It is not the same as your gross sales, a single order, the amount in your bank or your profit. One payout can cover several statements, and the bank may credit it after the statement is settled.</p>""", None),
    ("export-excel-csv", "Can I export TikTok Shop figures to Excel or CSV?",
     """<p>Yes. MyShopEdge builds Excel or CSV files from your shop's data:</p>
<ul><li><strong>Month summary</strong>, with the period's totals;</li><li><strong>Ledger</strong>, with every financial entry;</li><li><strong>Transactions</strong>, with one row per order line.</li></ul>
<p>You choose the period and the basis before the file is built. A month summary has the same totals as MyShopEdge shows for the same shop, period and basis.</p>""",
     f'<p>Build a reconciled file from your own shop: <a href="{START}">start your free 30-day trial</a>.</p>'),
    ("sales-vs-cash-basis", "What is the difference between sales basis and cash basis?",
     """<p><strong>Sales basis</strong> groups activity by the day of the sale. <strong>Cash basis</strong> groups it by the month TikTok Shop settled it. The same month can therefore show different totals on each basis.</p>
<pre class="calc">Sale date:         28 September
Settlement date:   6 October
Sales basis:       September
Cash basis:        October</pre>
<p>Cash basis in MyShopEdge is a way of reporting. It does not by itself mean your figures meet HMRC's cash basis rules for your circumstances.</p>""", None),
    ("export-differs", "Why does my TikTok Shop export differ from another report?",
     """<p>Check that you are comparing the same shop, the same dates, the same basis, the same update time and the same scope, whether sales, statements or payouts. Sales basis and cash basis can differ for the same calendar month.</p>
<p>If a MyShopEdge export does not match the MyShopEdge screen for the same shop, dates and basis, write to <a href="mailto:support@inspirecraftglobal.com">support@inspirecraftglobal.com</a> with the file and a screenshot.</p>""", None),
    ("payout-turnover-vat", "Does my TikTok Shop payout count as turnover for VAT?",
     """<p>Usually your payout is not your taxable turnover. A payout has already had commission, fees, refunds and adjustments taken off, while VAT registration looks at taxable turnover across your whole business over a rolling 12 months, not at what one marketplace paid into your bank.</p>
<p>MyShopEdge tracks the TikTok Shop turnover it holds against the VAT registration threshold as a planning tool. It does not decide whether you must register, and it does not prepare VAT returns.</p>""", None),
    ("vat-threshold-uk", "What is the TikTok Shop VAT threshold in the UK?",
     """<p>The UK VAT registration threshold is £90,000 of taxable turnover. It is measured over a rolling 12 months rather than a calendar year, and you may also need to register if you expect to pass it in the next 30 days alone.</p>
<ul><li>The threshold concerns taxable turnover, not the payout in your bank.</li><li>Sales on other channels count too.</li><li>Whether a sale is taxable can depend on the product, the customer and your circumstances.</li><li>Thresholds and rules change.</li></ul>
<p>MyShopEdge tracks the TikTok Shop turnover it holds, and lets you add sales from other channels. Check your full position with HMRC or a qualified accountant.</p>""", None),
    ("does-myshopedge-calculate-tax", "Does MyShopEdge calculate VAT, Income Tax or National Insurance?",
     """<p>MyShopEdge does not prepare or submit VAT returns, Income Tax returns or National Insurance. It tracks TikTok Shop turnover against the VAT registration threshold, and for sole traders it gives a planning estimate of an Income Tax and National Insurance set-aside. That estimate does not include Scottish Income Tax rates, other income, every expense, reliefs or personal circumstances. It is not tax advice.</p>""", None),
    ("replace-accountant", "Is MyShopEdge a replacement for an accountant or bookkeeping software?",
     """<p>No. MyShopEdge helps you understand and reconcile your TikTok Shop activity before you hand figures to a bookkeeper or accountant, and it builds summaries, ledgers and transaction files for them. It does not replace professional bookkeeping, statutory accounts, VAT or tax returns, tax or legal advice, or an accountant's review of your records.</p>""", None),
    ("vs-seller-center", "What does MyShopEdge do that TikTok Shop Seller Center does not?",
     """<p>Seller Center is the source of your shop's records. MyShopEdge organises those records into a seller's financial view. It lets you:</p>
<ul><li>see sales, every named deduction and net proceeds in one calculation;</li><li>explain a payout through its statements and transactions;</li><li>add your own product costs and see gross profit by product;</li><li>see where costs are missing;</li><li>record the effect of returns and write-offs;</li><li>export sales basis or cash basis files, and schedule them on the Pro plan;</li><li>follow your progress towards the VAT threshold.</li></ul>""",
     f'<p><a class="btn" href="{START}">Start your free 30-day trial</a></p>'),
    ("can-myshopedge-change-shop", "Can MyShopEdge change my TikTok Shop?",
     """<p>No. MyShopEdge only reads. It cannot place orders, issue refunds, change listings or prices, move money, change payouts or message customers. You can disconnect your shop under Settings, Shop connection, at any time.</p>""", None),
    ("what-data", "What data does MyShopEdge read from TikTok Shop?",
     """<p>With your approval, MyShopEdge reads your shop's orders and order lines, products, SKUs and stock, sales and seller discounts, refunds, cancellations and returns, fees and commissions, statements, settlements and payouts, and transaction adjustments.</p>
<p>TikTok Shop's records can include buyers' names, addresses and telephone numbers. MyShopEdge drops those details before anything is stored. Our <a href="/privacy">Privacy Policy</a> explains the rest.</p>""", None),
    ("free-trial", "How does the MyShopEdge 30-day free trial work?",
     """<p>You connect your TikTok Shop, choose a plan and give a card on MyShopEdge's billing page, where Stripe takes the card details. You pay £0 that day. The trial lasts 30 days, and your plan starts after it unless you stop it under Settings, Profile and plan before the trial ends. MyShopEdge never stores your card number or security code.</p>""", None),
    ("trial-ends", "What happens when my MyShopEdge trial ends?",
     """<p>If you have not stopped the plan, it starts and renews each month at its price, and you carry on without interruption. If you stopped it, the plan ends when the trial ends. Ending a plan does not delete your account or your records. If a payment fails, your figures stay open to you while you change the card.</p>""", None),
    ("delete-account", "Can I delete my MyShopEdge account and data?",
     """<p>Yes. Delete your account under Settings, Your data. You can cancel the deletion within 30 days; after that your name, email, connection tokens and files are erased. Some records are kept for a limited time for legal reasons, as our <a href="/privacy">Privacy Policy</a> explains. You can also write to <a href="mailto:privacy@inspirecraftglobal.com">privacy@inspirecraftglobal.com</a>.</p>""", None),
    ("contact-support", "How do I contact MyShopEdge support?",
     """<p>Write to <a href="mailto:support@inspirecraftglobal.com">support@inspirecraftglobal.com</a>. It helps to include your shop name, the dates, whether you were on sales basis or cash basis, the order, statement or payout reference, a screenshot, and a short note of what looks wrong.</p>
<p>Privacy requests go to <a href="mailto:privacy@inspirecraftglobal.com">privacy@inspirecraftglobal.com</a>, legal questions to <a href="mailto:legal@inspirecraftglobal.com">legal@inspirecraftglobal.com</a>, and general questions to <a href="mailto:info@inspirecraftglobal.com">info@inspirecraftglobal.com</a>.</p>""", None),
]

SOURCES = """<ul>
<li>TikTok Shop Seller Center, Finance: statements, settlement periods, payouts and the commission policy for your account.</li>
<li>GOV.UK, <a href="https://www.gov.uk/how-vat-works/vat-thresholds">VAT registration thresholds</a>.</li>
<li>GOV.UK, <a href="https://www.gov.uk/government/publications/rates-and-allowances-income-tax">Rates and allowances: Income Tax</a>.</li>
<li>GOV.UK, <a href="https://www.gov.uk/government/publications/rates-and-allowances-national-insurance-contributions">Rates and allowances: National Insurance contributions</a>.</li>
</ul>"""


def text(fragment: str) -> str:
    """The answer as plain text, for the JSON-LD, so it says exactly what the page says."""
    t = re.sub(r"<br\s*/?>", "\n", fragment)
    t = re.sub(r"</(p|li|tr|pre|ul|table)>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    return "\n".join(line.strip() for line in t.splitlines() if line.strip())


def build() -> str:
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": text(a)}}
            for _, q, a, _ in QA
        ],
    }
    crumbs = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "MyShopEdge",
             "item": "https://myshopedge.inspirecraftglobal.com/"},
            {"@type": "ListItem", "position": 2, "name": "TikTok Shop seller finance FAQ",
             "item": "https://myshopedge.inspirecraftglobal.com/faq/tiktok-shop-seller-finance"},
        ],
    }
    toc = "\n".join(f'<li><a href="#{a}">{html.escape(q)}</a></li>' for a, q, _, _ in QA)
    body = []
    for n, (anchor, q, a, cta) in enumerate(QA, 1):
        block = f'<details class="qa" id="{anchor}"{" open" if n == 1 else ""}>\n<summary>{n}. {html.escape(q)}</summary>\n<div class="answer">\n{a}\n</div>\n</details>'
        if cta:
            block += f'\n<div class="cta-block">{cta}</div>'
        body.append(block)
    return f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TikTok Shop Seller Finance FAQ: Payouts, Fees, Profit and VAT UK</title>
<meta name="description" content="Answers for UK TikTok Shop sellers on payouts, settlements, fees, refunds, net proceeds, gross profit, exports and the VAT threshold.">
<link rel="canonical" href="https://myshopedge.inspirecraftglobal.com/faq/tiktok-shop-seller-finance">
<link rel="icon" href="/brand/mse-favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&family=IBM+Plex+Sans:wght@400;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/pages.css">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
<script type="application/ld+json">{json.dumps(crumbs, ensure_ascii=False)}</script>
</head>
<!-- Generated by scripts/site/build_faq.py. Edit the questions there and run it again. -->
<body>
<header class="top"><div class="wrap">
<a href="/"><img src="/brand/mse-logo-horizontal-notagline.svg" alt="MyShopEdge"></a>
<nav aria-label="Main"><a href="/">Home</a><a href="{EXPLAINER}">Payout Explainer</a><a href="/#pricing">Pricing</a><a class="cta" href="{START}">Get started</a></nav>
</div></header>
<main class="wrap">
<h1>TikTok Shop seller finance FAQ: payouts, fees, profit and VAT</h1>
<p class="lede">Plain answers for UK TikTok Shop sellers on why a payout differs from sales, what TikTok Shop deducts, and how to work out what your products earn.</p>
<p class="meta">Written by the MyShopEdge editorial team. Last reviewed {REVIEWED}. Next review {NEXT_REVIEW}. This page is general information and is not tax, accounting or legal advice.</p>
<nav class="toc" aria-label="Questions"><ol>
{toc}
</ol></nav>
{chr(10).join(body)}
<h2>Sources and further reading</h2>
{SOURCES}
</main>
<footer class="bottom"><div class="wrap">
<span>&copy; 2026 Inspirecraft Global Ltd, company no. 16159924</span>
<span><a href="/privacy">Privacy</a> &middot; <a href="/terms">Terms</a> &middot; <a href="/cookies">Cookies</a></span>
</div></footer>
<script>
  // A link to #question opens that answer.
  function openHash() {{ var d = location.hash && document.getElementById(location.hash.slice(1)); if (d && d.tagName === "DETAILS") d.open = true; }}
  window.addEventListener("hashchange", openHash); openHash();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[2] / "site" / "faq" / "tiktok-shop-seller-finance.html"
    out.write_text(build(), encoding="utf-8")
    print(f"wrote {out} with {len(QA)} questions")
