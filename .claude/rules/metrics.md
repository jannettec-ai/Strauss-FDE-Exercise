# Metrics Dictionary — Strauss Negotiation Prep Packet

All KPI math in the codebase must match these definitions exactly.
Do not redefine a metric inline elsewhere.

---

## 1. Supplier Response Time

**Definition:** Average elapsed calendar days between an outbound Strauss
email (from: david.cohen@strauss-group.com) and the next inbound reply from
the same supplier thread, measured across all threads in the 6-month window.

**Formula:**
```
response_time_days = mean(
    reply_date - outbound_date
    for each (outbound, reply) pair in supplier thread
    where reply.from != "david.cohen@strauss-group.com"
    and reply is the first inbound message after outbound
)
```

**Source fields:** `date` field in email JSON, `from` field to determine
direction. Pairs are matched by thread (same subject root, chronological order).

**Unit:** Calendar days (float, rounded to 1 decimal place for display).

**Edge cases:**
- Unanswered outbound emails (no subsequent inbound): excluded from the mean,
  flagged separately as "unanswered threads."
- Same-day replies: result is 0 days (not excluded).
- Multiple inbound replies before next outbound: only the first reply counts.

---

## 2. Open Issues Count

**Definition:** Number of distinct unresolved threads or flagged items
identified by the AI extraction pass for a given supplier, as of the
most recent email date.

**What counts as an open issue:**
- A contract/email price discrepancy (quoted price differs from contract price
  without a documented written amendment)
- A delivery dispute with no written resolution in the thread
- A quality complaint with no accepted resolution
- A contract term in active renegotiation (no signed outcome)
- A renewal date discrepancy between email and contract
- A specification change proposed but not formally accepted via change order
- An expired contract with no active signed replacement

**Formula:** `open_issues = count(issues where status == "unresolved")`

**Source:** Output of `extraction.py` per supplier. Each issue has:
- `issue_type` (str): one of the categories above
- `description` (str): plain-language summary
- `source_ref` (str): e.g. "email dated 2026-03-07" or "contract Section 4.2"
- `status` (str): "open" | "resolved"

**Unit:** Integer count. Display alongside issue list, not as a standalone number.

---

## 3. Price vs. Contract Delta

**Definition:** The difference between the most recently quoted price in
supplier emails and the current contracted base price, expressed in both
absolute terms and percentage.

**Formula:**
```
delta_absolute = latest_quoted_price - contract_base_price
delta_pct = (delta_absolute / contract_base_price) * 100
```

**Source fields:**
- `contract_base_price`: extracted from the contract's Pricing section
- `latest_quoted_price`: most recent price figure found in supplier email
  thread by the extraction pass, with source email date and sender attributed

**Unit:** Same currency/unit as contract (e.g. $/ton, ₪/kg, PLN/unit).
Display as: "Contract: $398/MT | Latest quote: $420/MT | Delta: +$22/MT (+5.5%)"

**Edge cases:**
- If no price is quoted in email thread: show "no price quoted in emails"
- If quoted price matches contract: delta = 0, display "In line with contract"
- If multiple prices are quoted in thread: use the most recent by date
- If price unit is ambiguous in email (e.g. "per unit" vs "per MT"): flag
  as ambiguous, do not compute delta, surface the ambiguity as an open issue

---

## 4. Days to Contract Renewal

**Definition:** Calendar days from today's date to the contract's Renewal Date.

**Formula:**
```
days_to_renewal = contract_renewal_date - today
```

**Source fields:** `Renewal Date` from contract file. Today's date from system.

**Unit:** Integer days. Display as:
- Green: > 90 days
- Amber: 30–90 days ("renewal approaching")
- Red: < 30 days or already past ("renewal overdue / no active contract")

**Edge cases:**
- Split-file suppliers (Lowlands Dairy): if no active signed contract exists,
  display "NO ACTIVE CONTRACT" in red rather than a days count.
- Auto-renewal contracts: display days to renewal + "(auto-renews unless
  notice given by [date])" where notice date = renewal_date - notice_period_days.

---

## 5. Override / Correction Rate

**Definition:** Percentage of AI-extracted fields that the Procurement Manager
has manually corrected or flagged as wrong, out of total fields presented.

**Formula:**
```
correction_rate = (fields_flagged_or_corrected / total_fields_presented) * 100
```

**Source:** User interaction log (Streamlit session state). Each field in the
packet UI that the manager edits or flags increments `fields_flagged_or_corrected`.
`total_fields_presented` is the count of all extractable fields shown per packet.

**Unit:** Percentage (float, 1 decimal). Tracked per supplier and in aggregate.

**Purpose:** Trust signal for extraction quality. High correction rate on a
specific supplier or field type indicates extraction logic needs tuning.
Not shown in the packet UI itself — for internal monitoring only in this prototype.
