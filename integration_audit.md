# ⚠️ PHASE 2 STATUS — READ FIRST (updated 2026-10-09, work stopped early at the user's request)

**Backend: implemented and tested (44 pytest tests pass, run with no Gemini key). Frontend: NOT yet wired. `frontend/src/` is unchanged, so every frontend finding in §4 below still applies.** The older sections describe the *original* code; where the backend changed they are superseded by this section.

## Done in the backend (evidence: `backend/tests/`, `pytest -q` → 44 passed)
| Area | Change | Test evidence |
|---|---|---|
| D-01 datetime crash | All timestamps normalised to UTC in `Claim` | `test_mixed_naive_and_aware_timestamps_do_not_crash_the_backend` |
| D-02 data source | Queue built from the 4,950-claim CSV (203 cases, one per provider, ID `CASE-<npi>`); 3 injected fraud providers rank top 3 | `test_queue_is_built_from_the_real_dataset` |
| D-04/05 unknown IDs, graph | Unknown case → 404 on context, action, audit, brief, chat, graph. New case-specific graph from real claims | `test_graph_endpoint_is_case_specific`, `test_context_for_unknown_case_is_404...` |
| D-08 actions | Five actions supported: `APPROVE_SIU`, `REQUEST_INFO`, `DISMISS`, `REFER_SIU`, `PAUSE_PAYMENT`. Persisted status + payment-hold flag, 409 on illegal transitions, reason required. `DISMISS` releases a hold and is terminal. Holds are a recorded flag only; no payment system exists | `tests/test_workflow.py` |
| D-07 ledger | SQLite append-only audit ledger (UPDATE/DELETE blocked by triggers), survives restart | `test_ledger_is_append_only`, `test_audit_trail_records_real_actions_in_order` |
| D-09 AI honesty | Chat/brief use real case facts + retrieved policy passages, multi-turn history, 30 s timeout. Without a key they return `AI_UNAVAILABLE` / `source: FALLBACK`, `confidence_score` null/0 (the fake 0.92/0.88 is gone). Provider errors are not leaked | `tests/test_copilot.py` (uses a fake Gemini client) |
| D-10 policies | `GET /cases/{id}/policies`: TF-IDF retrieval over the real corpus | `test_structured_policy_retrieval_cites_real_corpus_text` |
| D-14 validation | `/analyze` rejects amount ≤ 0, empty fields. **Contract change:** `/analyze` is now a dry run; `?persist=true` stores the claim (409 on duplicate ID) | `test_analyze_*`, `test_persist_*` |
| D-17 forecast | 30-day minimum window; returns history series | `test_forecast_does_not_extrapolate_a_one_day_burst` |
| D-20 errors / CORS | JSON 500 with CORS header; CORS limited to localhost dev origins | code |
| D-22/D-28 tests | Order-independent, private DB, no key, no longer overwrite `data/` | whole suite |
| New endpoints | `GET /cases/{id}` (detail), `/cases/{id}/knowledge`, `/providers/{npi}`, `PUT /providers/{npi}/monitoring` (persisted watchlist, audited; **no alert delivery exists**), `/search`, `/stats`, `/audit` | smoke-run, partly tested |

## Not done — remaining work
1. **All frontend wiring** (Command Center, Case, Provider, Analyzer, Deep-Dive, Copilot, Audit, Brief, Settings, search, notifications). Nothing in `App.tsx` / `api.ts` was changed, and the old UI cannot send the new actions (`REFER_SIU`, `PAUSE_PAYMENT`), so it still shows the original fake successes and hardcoded data.
2. Settings/profile pages have no backend; plan is to keep them as clearly labelled local-only (localStorage) preferences.
3. Fraud-ring KPI cannot be derived (the synthetic data is one connected component); replace it with a real metric.
4. Live Gemini path is untested (no key used). Duplicate rule is a 5-minute window while the policy text says 24 hours (business decision). The delivered `backend/.env` holds a real key: rotate it (it is not in this zip).
5. Per-feature verification table for the frontend and a browser run have not been done.

---

# ClaimShield Nexus — Frontend ↔ Backend Integration Audit

**Scope:** `Final phase/frontend` (React 19 + TypeScript + Vite 8) and `Final phase/backend` (FastAPI)
**Audit date:** 2026-10-09
**Phase:** 1 of 2 — read-only audit. **No project source file was modified.** This document is the only addition to the project.

---

## 0. How to read this document

### Evidence levels

Every finding carries one of three tags, so confirmed defects are kept apart from suspected ones.

| Tag | Meaning |
|---|---|
| **[RUNTIME]** | Reproduced by executing the code (backend on a scratch copy, plus the built frontend in a headless browser against the live backend). |
| **[CODE]** | Confirmed by reading the source. Behaviour follows directly from the code, and no execution was needed. |
| **[NEEDS-RUNTIME]** | Plausible from the code but cannot be proven here. The reason is stated (for example, no usable Gemini key or network). |

### What was and was not done

- All source files were read in full: 732-line `App.tsx`, `api.ts`, every backend router, schema and service, the data generator, the data files and all five test files. Nothing was inferred from filenames.
- Runtime checks ran on **throwaway copies** in a scratch directory:
  - the backend with its `.env` removed, so the real Gemini key was never loaded or used;
  - the production build of the frontend;
  - a headless Chromium session clicking through the app against the live backend.
- `backend/.env` was **not read for its value**. Only whether the key is present and whether it differs from the placeholder was checked (see D-03).
- Because the Gemini key was removed, every AI path was exercised **only in its offline fallback**. The live Gemini path is **[NEEDS-RUNTIME]** throughout.
- `tsc --noEmit` passes and `vite build` succeeds. This proves nothing about integration, as the findings below show.

### Headline

The wire-level plumbing is mostly correct: all 10 frontend calls hit real backend paths with compatible payloads. The **application-level integration is not**. Of the 28 frontend features catalogued in §4, only a handful render real backend data end to end: the 3 live queue rows and the Request-records/Approve action write. The rest are hardcoded, partly wired with the response thrown away, or have no backend counterpart. The live backend itself has a crash that permanently breaks it after one normal analyzer submission. It also runs on a 3-claim hardcoded seed, not the 4,950-claim dataset sitting in `backend/data/`.

---

## 1. Architecture snapshot

```
Final phase/
├── frontend/   React SPA — everything lives in src/App.tsx (732 lines) + src/services/api.ts (169 lines)
│   └── dev server: Vite on PORT (default 8443, strictPort) — Figma Make scaffold
└── backend/    FastAPI "Unified Backend Hub" v3.0.0 — uvicorn app.main:app, port 8000
    ├── app/main.py            6 endpoints + lifespan seeding + CORS
    ├── app/routers/           cases_router (3 endpoints), copilot_router (1 endpoint)
    ├── app/services/          12 modules (rules, ML, ranking, forecast, graph, RAG, Gemini, audit…)
    ├── app/models/schemas.py  Pydantic models
    └── data/                  synthetic_claims.csv (4,950 rows), .json (unused), synthetic_policies.md (6 paragraphs)
```

- **No database.** All state is module-level Python lists and dicts, lost on restart.
- **No authentication.** There is no auth in the backend and none in the frontend.
- **Two disjoint data universes on the backend** (see D-02):

| Universe | Content | Used by |
|---|---|---|
| **A — in-memory seed** | 3 hardcoded claims (`main.py:53-58`), NPIs like `NPI-100`, `NPI-999`, `NPI-101`, plus whatever is POSTed to `/analyze` | queue, forecast, copilot context, analyze, ML, rules |
| **B — CSV dataset** | 4,950 claims, 203 providers, 10-digit NPIs like `1999999999` | graph export, centrality warm-up, historical memory |

The two share no keys. The CSV is never loaded into `CLAIM_DATABASE`.

---

## 2. Backend endpoint inventory

Auth: **none** on every endpoint. CORS: `allow_origins=["*"]` with `allow_credentials=True` (`main.py:92-98`).
Validation errors on all POST endpoints use FastAPI's default **422** `{"detail":[{type,loc,msg,input}…]}`.

| # | Method & path | Params / request schema | Response schema | Service(s) invoked | Error responses | Source |
|---|---|---|---|---|---|---|
| E1 | `GET /` | none | untyped `{status, system, version:"3.0.0", modules[]}` | none (static) | none | `main.py:105` |
| E2 | `POST /api/v1/analyze` | Body `Claim`: `claim_id`*, `provider_npi`*, `member_id`*, `facility_id?`, `cpt_code`*, `claim_amount`* (float, no bounds), `timestamp`* (datetime), `location`*, `diagnosis_code`* | `ClaimAnalysisResponse{claim_id, provider_npi, rule_flags{is_duplicate, impossible_geography, upcoding_anomaly, flag_count, flag_reasons[]}, anomaly_score{ml_score 0‥1, is_anomalous}}` | `evaluate_claim_rules`, `ml_service.predict`. **Side effect:** appends to `CLAIM_DATABASE` and both result maps | 422 on validation. **Unhandled 500** (`TypeError` naive/aware datetimes) — D-01 | `main.py:124` |
| E3 | `GET /api/v1/siu/queue` | none (no paging or filters) | `List[SIUCase]{case_id, provider_npi, member_id, total_claim_amount, rule_flag_count, ml_anomaly_score, graph_centrality, composite_risk_score, status:"OPEN", forecast?}` | `generate_siu_queue` → `calculate_provider_exposure` | **Unhandled 500** after naive/aware mix (D-01) | `main.py:142` |
| E4 | `GET /api/v1/cases/{provider_npi}/forecast` | path: provider **NPI** (not a case ID, despite the `/cases/` prefix) | `ExposureForecast{provider_npi, historical_daily_avg_claim, day_30/60/90_exposure}` | `calculate_provider_exposure` | 404 `{"detail":"Provider NPI … not found"}`. 500 after naive/aware mix | `main.py:153` |
| E5 | `GET /api/v1/copilot/context/{case_id}` | path: case ID | `CopilotContextPayload{case_id, provider_npi, member_id, total_claim_amount, composite_risk_score, rule_flag_count, rule_flag_reasons[], ml_anomaly_score, graph_centrality_score, projected_30d_loss, projected_90d_loss, associated_claim_ids[], policy_context_paragraphs[]}` | `generate_siu_queue`, `build_copilot_context` | 404 only if the queue is empty. **An unknown case ID silently returns the top-ranked case with 200** (D-04). `policy_context_paragraphs` are 2 hardcoded strings (`context_aggregator.py:49-52`) | `main.py:162` |
| E6 | `GET /api/v1/graph/export/{case_id}` | path: case ID. The service looks it up as a CSV **claim_id** | untyped `{case_id, nodes[{id,label,type,color,is_target}], edges[{source,target,label,claim_id}]}` | `build_claim_graph` (CSV → DiGraph, **rebuilt every request**, ~400 ms), `export_case_graph_json` | All exceptions → 500 `"Graph export error: {str(e)}"` (leaks internals). Unknown ID → silently returns the graph for the **first CSV claim** | `main.py:190` |
| E7 | `POST /api/v1/cases/{case_id}/action` | Body `CaseActionRequest{action, investigator_id="INV-DEFAULT", notes=""}`. `action` is validated in the handler, not the schema: `APPROVE_SIU` \| `REQUEST_INFO` \| `DISMISS` | untyped `{"status":"SUCCESS","audit_entry":{case_id, action, investigator_id, notes, timestamp}}` | `record_action` (in-memory list) | 400 `{"detail":"Invalid action…"}`. **No check that the case exists. No effect on case status** | `cases_router.py:10` |
| E8 | `GET /api/v1/cases/{case_id}/audit` | path | untyped `{case_id, audit_trail[entry…]}` | `get_case_audit_history` | none. Unknown case → 200 with `[]` | `cases_router.py:26` |
| E9 | `POST /api/v1/cases/{case_id}/brief` | Optional body `BriefRequest{case_id, claim_details, flagged_rules[]}`. The body may be omitted | `SIUBriefSchema{case_id, executive_summary, key_evidence[], policy_citations[], recommended_action, confidence_score}` | `generate_siu_brief` → `get_relevant_policies` (keyword RAG) → Gemini `gemini-2.5-flash` (structured JSON) | Gemini failure: `except Exception: pass` → canned fallback brief, still 200 (`brief_generator.py:65-66`). Guardrails are never applied to briefs | `cases_router.py:33` |
| E10 | `POST /api/v1/copilot/chat` | Body `CopilotChatRequest{case_id, message, chat_history[{role,content}]=[], case_context=""}` | `CopilotChatResponse{case_id, reply, status, confidence_score, disclaimer?}` | `apply_responsible_ai_guardrails`, `get_relevant_policies`, Gemini | Always 200. Gemini failure → canned reply (`copilot_router.py:83-93`) **still labelled `PASSED_GUARDRAILS` with `confidence_score` 0.92 hardcoded** (`:97-99`). Guardrail refusal → 200 with `status:"SAFETY_REFUSAL"` | `copilot_router.py:27` |

### Backend capabilities that exist but are not exposed by any endpoint

- `HistoricalCaseMemory.search_similar_precedents` (TF-IDF precedent search). It is instantiated at startup (`main.py:76`) and never queried.
- `detect_coordinated_fraud_rings` analysis (risk colours, connected components). It is used only to warm `GRAPH_CENTRALITY_MAP`, and only for CSV NPIs that no live claim carries.
- `get_relevant_policies` has no direct endpoint. It is reachable only through brief and chat.

### Backend capabilities the frontend shows that **do not exist** at all

Claims list or detail by provider/case; dashboard KPIs or stats; case status workflow; SIU referral; payment hold; provider profile and history; global search; notifications; user, profile or settings; login. `synthetic_claims.json` is generated and never read.

---

## 3. Frontend feature inventory

All UI is in `frontend/src/App.tsx`, and all network access goes through `frontend/src/services/api.ts`.

**Pages** (13 `Page` values, `App.tsx:4`): `command`, `case`, `provider`, `analyzer`, `brain`, `audit`, `brief`, plus six account-settings pages (`personal`, `access`, `regions`, `assignments`, `alerts`, `digest`). Routing is a `useState<Page>`. There is no router, no URLs and no deep links; a browser refresh returns to the login screen.

**Overlays:** global search modal, action dialog, copilot drawer, notification menu, profile menu, knowledge-search modal.

**Data-fetching operations** (every one is in `api.ts`): `health`, `queue`, `analyze`, `forecast`, `copilotContext`, `graph`, `action`, `audit`, `brief`, `chat`. A shared `request()` wrapper has a **6-second abort timeout** for all calls (`api.ts:40`), throws a generic `API request failed with status N` and discards the FastAPI `detail` body (`api.ts:52-54`).

---

## 4. Integration matrix

**Status key:** ✅ LIVE = real backend data is rendered. 🟡 PARTIAL = called, but the response is mostly or wholly discarded, or only one field is used. 🟥 MOCK = no backend call; hardcoded or computed in the UI. ⛔ BROKEN = wired but defective. ➖ NO BACKEND = the feature has no backend counterpart.

| ID | Frontend feature | Frontend file:lines | Backend endpoint | Backend service | Required input | Expected response | Status | Problems found (evidence) |
|---|---|---|---|---|---|---|---|---|
| F01 | App start: health + queue load | `App.tsx:695-702`, `api.ts:91-96` | E1 `GET /`, E3 `GET /siu/queue` | static; `generate_siu_queue` | none | `SIUCase[]` | 🟡 | Live rows are shown but **merged with 12 hardcoded `demoCases`** (`:698-699`; `demoCases` at `:10-23`). A run showed 15 rows: 3 live + 12 demo, with the header at "ENGINE ACTIVE" **[RUNTIME]**. `connected` is evaluated once at mount and never retried. |
| F02 | Login screen | `:102-123` | none | — | — | — | 🟥 ➖ | Hardcoded email and masked password rendered as `<div>`s, with a 750 ms timer then `setAuthenticated(true)`. "Protected by enterprise SSO · HIPAA-aligned session" is untrue **[CODE]**. |
| F03 | Header "ENGINE ACTIVE / DEMO MODE" pill | `:156` | derived from F01 | — | — | — | 🟡 | Logic is honest. The sidebar card (`:134`) and the banner "SUB-100MS COPILOT CONTEXT READY" (`:208`) are static and unconditional. |
| F04 | 4 KPI cards (1.84M claims, 1,284 flagged, $8.42M, 17 rings) | `:210-215` | none | — | — | — | 🟥 ➖ | Fully hardcoded, including trends and "vs. previous 30 days". The page eyebrow "MONDAY, 14 OCTOBER" is also hardcoded (`:209`); the actual date is Friday 9 Oct. |
| F05 | Priority queue table: search, risk filter, row select, double-click open | `:216-235` | E3 | `generate_siu_queue` | none | `SIUCase[]` | 🟡 | Search and risk filter are client-side only. **Status dropdown has no state or handler** (`:221`). "More filters", both "Refresh" buttons (`:209`, `:222-223`) and the row "…" button (`:231`) have no handler. "Live · updated 42s ago" is static (`:217`). Backend `status` is always `"OPEN"`, so status badges and filter semantics do not line up with the demo statuses. |
| F06 | "Create investigation" button | `:209` | none | — | — | — | ➖ | Opens the "Refer to SIU" dialog, which has no backend support (F13). |
| F07 | Case header + Evidence matrix + gauge | `:258-273`, `:416` | E3 data (already loaded) | — | `QueueCase` | — | 🟡 | The gauge labelled **"ML ANOMALY" renders the composite risk %** (`:267`), not `ml_anomaly_score`. "Rules triggered" come from a hardcoded per-case-ID map (`getTriggeredRules`, `:241-256`). For live cases the UI invents one rule named `"1 RULE-BASED FINDING"` from the flag string (`:255`). The real `rule_flag_reasons` from E5 are fetched and ignored. |
| F08 | Copilot-context prefetch on case open / drawer open | `:411-413`, `:671` | E5 | `build_copilot_context` | `case_id` | `CopilotContextPayload` | 🟡 | Response discarded; `.catch(() => undefined)`. The header pill says "Context ready" without using it. For unknown IDs (every demo case) the backend returns **another case's context with 200** **[RUNTIME]**. |
| F09 | Policy panel / "Policy Evidence" tab / Copilot "policies" | `:275-328`, `:420` | none | — | — | — | 🟥 | A 10-group hardcoded catalog of citations (CMS manuals, 42 CFR §1001.952, 31 USC §3729…) is presented as "**Grounded citations from approved policy corpus**" and "validated policy index · Last synchronized {today}". The backend corpus is 6 synthetic paragraphs, and none of these IDs exist in it. The "synchronized" date is `new Date()` (`:319`). |
| F10 | Linked claims table + "View all 6/48" | `:388-410`, `:418` | none (E5 has `associated_claim_ids` only) | — | — | — | 🟥 ➖ | Claim IDs, dates, CPTs and amounts are **fabricated by a deterministic formula**. Count is hardcoded 6 or 48. In a run, a live case showed `CLM-999201…` while the backend's only claim is `CLM-003` **[RUNTIME]**. There is no claims-by-case endpoint. |
| F11 | Fraud Network tab | `:330-358`, `api.ts:120` | E6 `GET /graph/export/{case_id}` | `build_claim_graph`, `export_case_graph_json` | `case_id` | `{nodes, edges}` | ⛔ | Payload is used for **one integer** (node count). The graph itself is a **static SVG** with 6 hardcoded nodes (`:339-346`). "32 relationships · 7 suspicious links", node detail "NPI 1029384 / $2.48M / 12 direct · 31 indirect" and the buttons −/+/Fit/refresh/"Open entity profile" are all static or dead. Backend returns the **wrong graph for every UI case ID** (D-05). |
| F12 | Financial Forecast tab: tiles, chart, range tabs, what-if slider | `:360-382`, `api.ts:114` | E4 `GET /cases/{npi}/forecast` | `calculate_provider_exposure` | provider NPI | `ExposureForecast` | 🟡 | Only `day_90_exposure` is read (`:366`). The four tiles ($18,420; $552,600; $1.08M; $1.64M), chart paths, "CONFIDENCE 89%" and the "$18,420 … +38% vs peer" subtext are hardcoded (`:372-380`). The 30D/60D/90D tabs change only a CSS class. "Projected 90-day savings" is a **UI formula with an arbitrary ×2.4 multiplier** (`:370`) shown as a projection. Default exposure is 1,640,000 until a response arrives or when it fails. Every demo case returns 404, swallowed **[RUNTIME]**. |
| F13 | Sticky actions: False positive, Approve, **Refer to SIU** | `:422`, `:643-657`, `api.ts:123` | E7 `POST /cases/{id}/action` | `record_action` | `action`, `investigator_id`, `notes` | `{status, audit_entry}` | 🟡 ⛔ | Mapping covers only 3 labels (`:647-651`). **"Refer to SIU" (the primary CTA) has no mapping**, so when connected it goes straight to an error state without any request **[RUNTIME]**. "Approve" maps to `APPROVE_SIU`, a semantics mismatch. The success toast claims "Compiling action into Institutional Knowledge Vault (NPI-….md)" (`:726`), which no backend does. Case status is never changed server-side, so the UI keeps `OPEN`. |
| F14 | Request records button | `:416` | E7 (`REQUEST_INFO`) | `record_action` | as F13 | as F13 | ✅ | A real POST succeeded and was recorded in the ledger **[RUNTIME]** (with "Approve"). |
| F15 | Pause payment button | `:416`, `:656` | none | — | — | — | ➖ ⛔ | No endpoint. Connected: always shows an error. Offline: shows a **fake success** (F13 note). |
| F16 | Ask Copilot drawer: chips, free-text box, guardrail test | `:659-682`, `api.ts:156` | E10 `POST /copilot/chat` | guardrails, RAG, Gemini | `case_id`, `message`, `chat_history`, `case_context` | `CopilotChatResponse` | 🟡 ⛔ | `api.chat` is awaited and **the response is thrown away** (`:672`). The UI renders canned text computed from `QueueCase`. The textarea is uncontrolled (`defaultValue`) and the send button always asks the same fixed "provider" question (`:681`). The user's typing is never sent. `chat_history` and `case_context` are never supplied. `try/catch` swallows all errors. |
| F17 | Executive Case Brief page: Regenerate, Copy, Export PDF | `:595-600`, `api.ts:143` | E9 `POST /cases/{id}/brief` | `generate_siu_brief` | `case_id`, `claim_details`, `flagged_rules` | `SIUBriefSchema` | 🟥 ⛔ | The page is a hardcoded `CASE-001` document (8 sections, "Generated Oct 14, 2026 at 10:48 AM", "Brief quality 96%", "Citations verified against policy corpus"). Regenerate always calls `api.brief("CASE-001")` with the fixed payload `"Investigation details for case X"` / `["ANOMALOUS_BILLING"]`, then ignores the result (`:597`). "Copy brief" has no handler. "Export PDF" is `window.print()`. |
| F18 | Provider Intelligence page: KPIs, behaviors, exposure, history, Monitor toggle | `:426-450` | none | — | — | — | 🟥 ➖ | Claim count = `risk*38+620`; average claim = billed ÷ that count; forecast = `billed*(1.35+risk/100)`; confidence = `risk+7`. All are **frontend inventions shown as metrics**. The "Prior investigations" table (names, dates, AI confidence) is hardcoded. "Monitor provider" is local state only. |
| F19 | Claim Analyzer: form + "ANALYZE CLAIM" | `:452-493`, `api.ts:98` | E2 `POST /analyze` | rules, ML | `Claim` | `ClaimAnalysisResponse` | ⛔ | The POST is made, but the **response is discarded** (`:475`). The result card shows `resultRisk`, which is computed locally from the *scenario button* or the selected case's risk (`:473`). It is labelled "LOCAL DEMO PREVIEW" even on success. On a live NPI the POST **corrupts the backend** (D-01) **[RUNTIME]**. `facility` (a name field) is sent as `facility_id`; `metadata` and `notes` are never sent. Claim IDs are random UUIDs. |
| F20 | Demo scenario buttons | `:462-471`, `:477` | none | — | — | — | 🟥 | Pre-fill the form. Honestly labelled "demo scenario". |
| F21 | Deep-Dive Workspace: tabs, synthesis, entities, backlinks, knowledge search | `:495-533` | none (`HistoricalCaseMemory` unexposed) | — | — | — | 🟥 ➖ | The "AI synthesis" is a template string (`:504-506`). Entity count = `risk/7`. The entities and claims lists are generated rows. Search filters a local array. Nothing here is AI- or backend-derived. |
| F22 | Audit Trail: table, filters, timeline, Export CSV | `:535-593`, `api.ts:140` | E8 `GET /cases/{id}/audit` | `get_case_audit_history` | `case_id` | `{case_id, audit_trail[]}` | ⛔ | The result is used only to flip a badge to **"LIVE LEDGER"** (`:590`). The events shown are **fabricated** from case fields with timestamps "2/7/14/28 minutes ago" and an attributed investigator "Maya Chen" (`:545-558`). **The real `APPROVE_SIU` entry just recorded did not appear** **[RUNTIME]**. "Export audit log" exports the fabricated rows. The "IMMUTABLE EVENT LEDGER" and "VERIFIED LEDGER" labels are unfounded. |
| F23 | Global search modal | `:638-641` | none | — | — | — | 🟥 ➖ | Static results (CASE-001, Dr. Alex Mercer, Ring East Coast 01). It ignores the typed text beyond showing/hiding. |
| F24 | Notifications menu | `:144-165` | none | — | — | — | 🟥 ➖ | 3 hardcoded notifications. |
| F25 | Settings pages ×6 + Save | `:609-636` | none | — | — | — | 🟥 ➖ | Uncontrolled inputs. "Save changes" shows the toast "preferences were saved to the secure audit log" (`:713`) but saves nothing. |
| F26 | Sign out / sidebar navigation / collapse | `:125-138`, `:716` | none | — | — | — | 🟥 | Local state only (acceptable for navigation). |
| F27 | "Create investigation case" in analyzer result | `:492` | none | — | — | — | ➖ | No handler. |
| F28 | Case "…" menu, Graph tool buttons, "Open entity profile", "Manage notification preferences" etc. | various | none | — | — | — | 🟥 | Placeholder buttons with no behaviour. |

**Real end-to-end behaviours today:** F01 (partial), F05 queue rows (3 live rows), F14 (Request records, and Approve) → ledger write, and the backend side of E1/E3/E4/E7/E8 as standalone endpoints.

---

## 5. Contract agreement check

| Dimension | Result | Detail |
|---|---|---|
| **API paths** | ✅ Agree | All 10 `api.ts` paths and methods match the backend (`/`, `/api/v1/siu/queue`, `/analyze`, `/cases/{npi}/forecast`, `/copilot/context/{id}`, `/graph/export/{id}`, `/cases/{id}/action`, `/audit`, `/brief`, `/copilot/chat`). **[RUNTIME]** Each returned 200 against the live backend, except where noted. |
| **Base URL** | ⚠️ Undocumented | `VITE_API_BASE_URL`, default `http://127.0.0.1:8000` (`api.ts:1`). There is no frontend `.env.example` and no README. |
| **Payload field names** | ✅ Mostly agree | `analyze`, `action`, `brief` and `chat` bodies use the exact snake_case names the Pydantic models expect. Extra form fields (`metadata`, `notes`) are dropped silently (no backend field). |
| **Field semantics** | ❌ Disagree | Analyzer sends a facility **name** as `facility_id` and a "Patient P-1872" label as `member_id`. Chat omits `case_context`, so the backend injects a fabricated default into every Gemini prompt: `'Flagged for impossible travel and duplicate billing.'` (`copilot_router.py:56`). Brief sends fixed fake details and the rule `ANOMALOUS_BILLING`. |
| **Case ID format** | ❌ Disagree | Backend: `CASE-{npi[-5:]}` (`siu_ranking.py:41`), e.g. `CASE-I-999` from `NPI-999`. Frontend demo: `CASE-001…012`. Graph service expects a CSV `claim_id` like `CLM-4A00B33B`. Three incompatible ID systems. The backend ID is also lossy: two NPIs sharing their last 5 characters collide (none do in the CSV set; synthetic `NPI-…` seeds are not safe). |
| **NPI format** | ❌ Disagree | Three formats: backend seed `NPI-100`, CSV 10-digit `1999999999`, frontend demo 7-digit `1029384`. Real NPIs are 10 digits. |
| **Enums: case status** | ❌ Disagree | Backend: single constant `"OPEN"`. Frontend demo: `Under Review / Pending Records / Triage / Escalated / Referred to SIU`. No status machine exists. |
| **Enums: actions** | ❌ Disagree | Backend `APPROVE_SIU / REQUEST_INFO / DISMISS`. Frontend `Approve / Request Medical Records / Mark False Positive / Refer to SIU / Pause Payment`. Two have no mapping. "Approve" → `APPROVE_SIU` is semantically unclear. |
| **Enums: rule vocabulary** | ❌ Disagree | Backend rules: duplicate, impossible geography, upcoding only. UI shows ~20 rule names (phantom billing, unbundling, modifier misuse, referral concentration, DME pattern, identity mismatch…) that no backend rule produces. Brief fallback keys on the substrings `"UPCODING"` / `"PHANTOM"` (`brief_generator.py:74`), which the rules engine never emits (it emits sentences and boolean fields). |
| **Risk scale** | ⚠️ Fragile | Backend 0‥1; `normalizeQueueItem` multiplies by 100 only if `≤ 1` (`api.ts:71`). |
| **`rule_flag_count` meaning** | ❌ Inconsistent *within the backend* | Queue = **max flags on any single claim** (0‥3). Context = **count of unique reason strings across all claims**. The same case can show different counts. |
| **Timestamps** | ❌ Disagree | Frontend sends `YYYY-MM-DDT00:00:00Z` (timezone-aware). Backend seed claims use `datetime.now()` (naive). Mixing crashes the backend (D-01). |
| **Response shapes** | ✅ Agree | `SIUCase`, `ExposureForecast` (`day_90_exposure` is read first in a 4-name fallback chain), `nodes[]` all match. Frontend `BackendQueueCase` only models 7 of the 10 queue fields, so `member_id`, `graph_centrality` and `forecast` are never used. |
| **Error handling** | ❌ Disagree | Backend emits `{"detail": str | list}` with 400/404/422/500. Frontend discards the body and reports a generic status string, then mostly swallows it. Distinct failures all become "Unable to complete this action. Check your connection and retry." (`:656`). |
| **500 responses in the browser** | ❌ | An unhandled exception's 500 carries **no CORS headers**, so the browser reports a failed fetch. After the D-01 crash the UI flips to "**DEMO MODE · API unavailable**" and 12 rows **[RUNTIME]**. A server bug looks like an offline server. |
| **Timeouts** | ⚠️ **[NEEDS-RUNTIME]** | The client aborts after 6 s for all calls (`api.ts:40`). The backend makes blocking Gemini calls with no timeout. A slow Gemini response on `/brief` or `/chat` would be aborted client-side and swallowed. |
| **Versions** | ⚠️ | UI shows "v3.5.0" in 4 places; the backend reports `3.0.0`. |

---

## 6. Hardcoded data, mocks, fake successes and swallowed exceptions

### 6.1 Hardcoded / demo data presented as real

| Location | What | Presented as |
|---|---|---|
| `App.tsx:10-23` | 12 `demoCases` (providers, NPIs, $ amounts, risk, status) | Live investigation queue (merged with real rows, `:698`) |
| `App.tsx:211-214`, `:209`, `:217`, `:208` | KPIs, date, "updated 42s ago", "SUB-100MS" | Live metrics |
| `App.tsx:241-256` | Per-case triggered rules | "Explainable evidence" |
| `App.tsx:278-318` | Policy catalog with CMS / CFR / USC citations | "Grounded citations from approved policy corpus" |
| `App.tsx:388-410` | Generated linked claims | "Claims under review" |
| `App.tsx:339-356` | Static graph, "32 relationships · 7 suspicious", NPI 1029384, $2.48M | "Fraud network" |
| `App.tsx:372-380` | Forecast tiles, chart, "CONFIDENCE 89%" | Provider financial exposure |
| `App.tsx:432-449` | Provider metrics and prior investigations | "Provider intelligence" |
| `App.tsx:504-506`, `:509-530` | Template "AI synthesis", generated entities/claims | "AI synthesis", "institutional memory" |
| `App.tsx:545-558` | Fabricated audit events, "Maya Chen" | "Immutable event ledger" |
| `App.tsx:598-599` | Entire CASE-001 brief + "96% quality" | "AI-generated · evidence grounded" |
| `App.tsx:144-148`, `:640` | Notifications, search results | Live |
| `App.tsx:627-632` | Investigator profile, regions, phone | Account data |
| `backend/main.py:35-42` | `GRAPH_CENTRALITY_MAP` hardcoded values for `NPI-999`=0.85, `NPI-100`=0.20, etc. | Graph centrality in the composite risk score |
| `backend/main.py:53-58` | 3 seed claims | The "claim database" |
| `backend/context_aggregator.py:49-52` | 2 hardcoded policy strings (NCD 190.3, FWA Rule 42) | `policy_context_paragraphs` |
| `backend/copilot_router.py:56` | Default case context text | Case context in Gemini prompt |
| `backend/graph_analytics.py:141` | `"1999999999" in node_id` → special colour | "High-risk" node colour |

### 6.2 Fake or misleading success

| Location | Behaviour |
|---|---|
| `App.tsx:653` | When `connected` is false, **every** action dialog (including Pause Payment and Refer to SIU) shows success after a 700 ms timer, with no request made. The success text is the only place it says "Demo action prepared". |
| `App.tsx:719-727` | Offline "Refer to SIU": **locally sets status to "Referred to SIU"** and toasts "SIU referral delivered … awaiting human verification". |
| `App.tsx:726` | Toast "Compiling action into Institutional Knowledge Vault (NPI-….md)…". No such feature exists. |
| `App.tsx:713` | Settings save: "saved to the secure audit log". |
| `App.tsx:590` | `LIVE LEDGER` badge turns on for **any 200 from the audit endpoint**, even with zero entries. |
| `backend/copilot_router.py:97-99` | Canned fallback reply is returned with `status:"PASSED_GUARDRAILS"` and `confidence_score:0.92` (hardcoded). |
| `backend/brief_generator.py:75` | Fallback brief returns `confidence_score:0.88` hardcoded. |
| `backend/main.py:134-139` | `/analyze` returns success and mutates global state for a claim with a negative amount (verified) **[RUNTIME]**, and for a re-posted duplicate `claim_id`. |

### 6.3 Swallowed exceptions

| Location | Effect |
|---|---|
| `App.tsx:337`, `:368`, `:412`, `:590`, `:671` | `.catch(() => undefined)` on graph, forecast, context and audit. Failures are invisible to the user. |
| `App.tsx:597` | `catch { /* demo brief remains available offline */ }`: Regenerate "succeeds" regardless. |
| `App.tsx:672` | `catch { /* Preserve the safe… demo response offline */ }`: chat always "answers". |
| `App.tsx:475` | Analyzer error is shown, but the result card then renders anyway (`finally { setResult(true) }`). |
| `backend/brief_generator.py:65-66` | `except Exception: pass`: any Gemini error, bad JSON or schema mismatch silently becomes the canned brief. |
| `backend/copilot_router.py:23, 83` | The same pattern for client creation and generation. |
| `backend/main.py:71-72, 77-78` | Lifespan graph and memory warm-up errors are only printed. |
| `backend/graph_analytics.py:111-115` | Unknown case ID silently falls back to `df.iloc[0]`. |
| `backend/main.py:172-177` | Unknown case ID silently falls back to `siu_queue[0]`. |
| `backend/policy_rag.py:19` | A missing policy file yields the string `"Policy documentation file not found."` as if it were policy text. |

### 6.4 Frontend calculations presented as backend results

Provider claim count, average claim and 90-day forecast (`:433-435`); "Projected 90-day savings" (`:370`); entity and backlink counts (`:502-503`); confidence percentages (`:448`); analyzer risk score (`:473`); the "ML ANOMALY" gauge (`:267`).

---

## 7. Confirmed defects register

Priority: **P0** = blocks real use or misrepresents data as real. **P1** = major functional gap. **P2** = quality, robustness or hardening.

### P0

| ID | Evidence | Defect |
|---|---|---|
| **D-01** | [RUNTIME] | **One analyzer submission crashes the backend permanently.** The frontend sends `timestamp` as `…T00:00:00Z` (aware). The seed claims use `datetime.now()` (naive). `rules_engine.py:25,34` and `forecasting.py:22` subtract or compare timestamps without normalising. Reproduced: POST `/analyze` for `NPI-100` returns 200 and appends the claim, then **`/siu/queue`, `/cases/NPI-100/forecast` and `/copilot/context/*` all return 500** (`TypeError: can't compare offset-naive and offset-aware datetimes`). A second POST using member `MEM-200` returns 500 (`can't subtract…`). The poisoned claim stays in memory until restart. In the browser this shows as "DEMO MODE" (500s lack CORS headers). Live NPIs are the first rows in the queue, so this is easy to hit. |
| **D-02** | [CODE]+[RUNTIME] | **The "live" queue is built from 3 hardcoded claims, not the dataset.** `CLAIM_DATABASE` is seeded with 3 rows (`main.py:53-58`). The 4,950-claim CSV feeds only the graph, centrality warm-up and historical memory, none of which share an ID with the queue. Warm-up writes ~200 centrality values keyed by 10-digit NPI that no queue claim uses. |
| **D-03** | [CODE] | **`backend/.env` is inside the delivered zip and contains a non-placeholder `GEMINI_API_KEY`** (present, 53 chars, differs from the template value; value not displayed). The backend `.gitignore` deliberately leaves `.env` tracked (its comment says so) and there is no root `.gitignore`. Treat the key as exposed: **rotate it** and stop distributing `.env`. |
| **D-04** | [RUNTIME] | **Unknown IDs silently return another case's data.** `/copilot/context/CASE-001` returns the context for `CASE-I-999` with 200. `/graph/export/<anything>` returns the first CSV claim's graph with 200. `/cases/<anything>/action` records an audit entry for a nonexistent case. Every demo case triggers this. |
| **D-05** | [RUNTIME] | **Graph endpoint cannot serve a case.** It looks up a CSV `claim_id`, while queue case IDs are `CASE-<npi tail>`. Result: the same fallback graph (28 nodes, 58 edges, anchored on `PROV_1000000161`) for `CASE-I-999`, `CASE-001` and any unknown ID. The endpoint builds a **DiGraph** (`graph_engine.py`) but reads node names from the `name` attribute, which that graph stores as `label`. Every node `label` therefore equals its raw ID. Neighbour lookup uses `G.neighbors` on the directed graph (successors only). The graph is rebuilt from CSV on **every request** (~400 ms measured vs ~3 ms for the context endpoint). The existing test for the export checks a *different* graph (undirected). |
| **D-06** | [CODE] | **Demo data is mixed into the live queue and labelled live.** Real rows are concatenated with 12 `demoCases` (`App.tsx:698`). The header shows "ENGINE ACTIVE" and "Context ready". 80% of rows have no backend identity. |
| **D-07** | [CODE]+[RUNTIME] | **The audit trail shows invented events and hides real ones.** Real ledger entries are fetched (`api.audit`) but never rendered. The UI invents 4 events with invented times and attributes them to "Maya Chen". The CSV export contains only the invented rows. The "LIVE LEDGER / IMMUTABLE" labels are false. |
| **D-08** | [CODE]+[RUNTIME] | **Primary workflow actions are unsupported and fake-succeed.** "Refer to SIU" and "Pause payment" have no endpoint; when connected they error without a request. When not connected, every action reports success after a timer. Offline "Refer to SIU" changes local status and toasts "referral delivered". Backend `action` never updates case status (queue stays `OPEN`). |
| **D-09** | [CODE] | **AI features are decorative.** Copilot chat and Executive Brief call the backend and ignore the response. The chat box content is never sent. The brief page is a static CASE-001 document. Nothing the user types or generates reaches Gemini or the guardrails. Brief and chat never receive the real case context from E5, so the model is never grounded in case data (and chat injects a fabricated default context). |
| **D-10** | [CODE] | **Policy "citations" are not from the backend corpus.** The frontend shows real-looking CMS, CFR and USC references under "approved policy corpus". The backend corpus is 6 synthetic paragraphs. Presenting unverified regulatory citations as grounded evidence is a trust and compliance risk in a fraud-investigation product. |

### P1

| ID | Evidence | Defect |
|---|---|---|
| D-11 | [CODE] | **Analyzer discards the real analysis.** `api.analyze` returns rule flags and an ML score, and the UI renders a locally computed score instead. Even on success the card says "LOCAL DEMO PREVIEW". The analysis never reaches the queue, because centrality and the ML model are not updated. |
| D-12 | [CODE] | **Missing endpoints for features the UI shows:** case detail with rule reasons and ML score; claims by case/provider; KPI stats; case status and referral workflow; payment hold; provider profile and history; global search; historical precedents; policy search; login. |
| D-13 | [CODE] | **Case ID design is unsound.** `CASE-{npi[-5:]}` is truncated, produces odd IDs (`CASE-I-999`), is not guaranteed unique, and one case equals one provider with a single arbitrary `member_id` (first claim's). |
| D-14 | [RUNTIME] | **Input validation gaps.** Negative `claim_amount` is accepted. Duplicate `claim_id` re-posts are appended again. No bounds on strings or `notes`. `action` is validated outside the schema, so OpenAPI shows an unconstrained string. |
| D-15 | [CODE] | **Rule-engine semantics.** Duplicate rule uses a 5-minute window, while the policy text states 24 hours. Geography flags any location difference within 2 h (no distance). Benchmarks exist for 3 CPT codes; the CSV uses others (71045, 93000, …) and falls back to a default $150. No phantom-billing rule exists although 60 CSV rows are `PHANTOM_BILLING`. `rule_flag_count` means different things in queue and context (see §5). |
| D-16 | [CODE] | **ML model is fit on 3 claims** at startup and never refit. Posted claims are not added to the model. Scores are not meaningful at this size. |
| D-17 | [CODE] | **Forecast math.** A provider with one claim gets a 1-day floor, so a single $5,000 claim projects to **$450,000 over 90 days** (seen in the live queue). Unrealistic, and unlabelled as such. |
| D-18 | [CODE] | **State is in-memory and shared:** the audit ledger, claims and results vanish on restart; no locking; each `lifespan` run re-extends `CLAIM_DATABASE` (duplicate seeds). |
| D-19 | [CODE] | **No authentication or authorization.** Login is cosmetic. `investigator_id` comes from the client (hardcoded `INV-DEFAULT` in the frontend), so audit attribution is spoofable. CORS is `*` with credentials. Chat history and `case_context` flow unescaped into the LLM prompt (prompt injection surface). |
| D-20 | [CODE] | **Unhandled exceptions return a bare 500** with no CORS headers and no JSON body; the graph endpoint returns raw `str(e)`. |
| D-21 | [CODE] | **Frontend error handling is generic**, hides `detail`, and swallows most failures (§6.3). Connectivity is checked once at mount with no retry, so a restarted backend still shows "DEMO MODE" until a full reload. |
| D-22 | [RUNTIME] | **Tests give false confidence.** 18 pass in order, but `test_siu_queue_ranking` and `test_copilot_context_payload_and_latency` **fail when run alone**. Tests use `TestClient(app)` without a context manager, so `lifespan` never runs and they pass only through state leaked from earlier tests. No test exercises the frontend contract, a naive/aware mix, or unknown IDs. |

### P2

| ID | Evidence | Defect |
|---|---|---|
| D-28 | [RUNTIME] | **Running the test suite replaces the project's dataset.** `tests/test_data_gen.py` calls `generate_synthetic_dataset`, which writes into the real `backend/data/` folder. Claim IDs use unseeded `uuid.uuid4()` (`generate_claims.py:94,111,130`), so every `pytest` run produces a different `synthetic_claims.csv` / `.json` (confirmed: the file differed in size and content after one run). Claim IDs, graph nodes, historical-memory results and anything keyed on them change under the user whenever tests run. The unpinned `faker` version adds further drift. |
| D-23 | [CODE] | RAG scoring uses substring matches over all tokens including stopwords, so results are noisy. `policy_citations` in the brief are raw markdown paragraphs including `##` headings. Brief `case_id` from Gemini is not forced to equal the path ID. Guardrails are keyword-only and never applied to briefs. `SAFETY_REFUSAL` returns `disclaimer: null`. |
| D-24 | [CODE] | `GRAPH_CENTRALITY_MAP` is keyed to CSV NPIs that never match; `HISTORICAL_MEMORY`, `get_relevant_policies` import in `main.py`, `os`, `Any` are unused. `synthetic_claims.json` is unused. |
| D-25 | [CODE] | Single 732-line `App.tsx` with ~30 inline components; no router (no URLs, refresh = logout); no frontend tests or lint script; `dist/` and a 84 MB Windows-built `node_modules` (win32 native bindings) are shipped in the zip. |
| D-26 | [CODE] | Dependencies unpinned in `requirements.txt` (`>=`), `pytest` listed as a runtime dependency, no Python version stated, no README, no Dockerfile, no frontend `.env.example`. |
| D-27 | [CODE] | UI shows v3.5.0 everywhere; API reports 3.0.0. Static strings such as "SUB-100MS" and "1.8M adjudicated claims" are not measured. |

### Issues that require runtime testing (not yet provable)

| ID | Question |
|---|---|
| R-01 | **Live Gemini path:** do `response_schema=SIUBriefSchema` and `gemini-2.5-flash` work with the installed unpinned `google-genai`? Does the response's `case_id` match? Needs a valid key and network. |
| R-02 | **Latency vs the 6 s client timeout** for `/brief` and `/chat` with real Gemini. |
| R-03 | Behaviour under concurrent requests (unsynchronised global lists). |
| R-04 | Real-browser UX on the Windows environment the project was built on (the shipped `node_modules` is win32). |
| R-05 | Performance of graph export at larger data sizes (full CSV re-read and `iterrows` per request; ~400 ms at 4,950 rows). |

### What works (kept as-is)

Path and method agreement for all 10 calls; request bodies for action, brief and chat; `ExposureForecast` and queue field names; action → ledger write; guardrail refusal for clinical prompts; CORS preflight from the dev origin; TypeScript compiles; `dist/` matches a fresh build.

---

## 8. Prerequisites for the real application to work

### 8.1 Environment variables

| Variable | Where | Required | Notes |
|---|---|---|---|
| `GEMINI_API_KEY` | `backend/.env` (loaded by `python-dotenv`) | Needed for real AI output. Without it (or if equal to `YOUR_GEMINI_API_KEY_HERE`) the app silently serves canned fallbacks | `.env.example` exists. A non-placeholder key is shipped inside the zip (D-03). |
| `VITE_API_BASE_URL` | frontend (`import.meta.env`) | Optional. Default `http://127.0.0.1:8000` | Undocumented; no frontend `.env.example`. |
| `PORT` | Vite dev / preview | Optional. Default `8443`, `strictPort: true` | Figma Make scaffold. |
| `FIGMA_PUBLIC_URL`, `FIGMA_DEV_SERVER_HOST` | `vite.config.ts` | Tooling only | Not needed for the app logic. |

### 8.2 Data and persistence

- **No database is required or present.** Persistence (audit ledger, claims, case status) does not exist.
- `backend/data/synthetic_claims.csv` is required by graph export, centrality warm-up and historical memory (columns: `claim_id, provider_npi, provider_name, member_id, facility_id, claim_timestamp, cpt_code, claim_amount, location_city, fraud_flag`).
- `backend/data/synthetic_policies.md` is required by the RAG. If missing, the string "Policy documentation file not found." becomes policy text.
- `synthetic_claims.json` is unused. `scripts/generate_claims.py` regenerates both files (needs `faker`).

### 8.3 Models and external services

- **IsolationForest** is trained in memory at startup on 3 seed claims. There is no model file or persistence.
- **TF-IDF** memory is built in memory from the CSV.
- **Gemini** `gemini-2.5-flash` via `google-genai` (outbound HTTPS to Google). It is hardcoded in two files.
- No other external API.

### 8.4 Runtime and toolchain

- Backend: Python 3 (3.13 used here), `pip install -r backend/requirements.txt`, then from `backend/`: `uvicorn app.main:app --port 8000`. Data paths resolve relative to the module files, and `.env` is found by walking up from `app/`, so the working directory is not critical.
- Frontend: Node 22 and pnpm (`frontend/.mise.toml` pins pnpm 10.34.3), `pnpm install`, `pnpm dev` (port 8443). The shipped `node_modules` is Windows-built and must be reinstalled elsewhere.
- Both must run together. The backend CORS permits the dev origin.

---

## 9. Prioritized remediation plan

**Rules for the fix phase:** preserve the existing UI, layout, styling and every intended feature. Replace hardcoded content with backend data **behind the same components**. Change one defect at a time and verify each with the checks listed. The user prefers granular, one-change-at-a-time iteration.

### Decisions needed from you before Phase 1

1. **Source of truth for claims.** Should the queue be built from the 4,950-claim CSV (recommended: it is the only realistic data) or from the 3-claim seed?
2. **"Refer to SIU" and "Pause payment".** Add real endpoints and statuses, or map them onto the existing three actions? (Recommended: add explicit actions `REFER_SIU` and `PAUSE_PAYMENT`, and a persisted status.)
3. **Offline/demo mode.** Keep an explicit, clearly labelled demo mode for presentations (recommended), or remove demo data entirely?
4. **Persistence.** Is SQLite acceptable for cases, claims and audit entries?
5. **Authentication scope.** Real login now, or defer and clearly mark the screen as a placeholder?

### Phase 0 — Hygiene (no behaviour change)

1. Rotate the Gemini key. Stop shipping `backend/.env`. Add a root `.gitignore` covering `.env`, `node_modules`, `dist`. *(D-03)*
2. Add `frontend/.env.example` (`VITE_API_BASE_URL`) and a short README with run commands. *(D-26)*

### Phase 1 — Backend foundation (fix what the frontend depends on)

| Step | Change | Fixes | Verify |
|---|---|---|---|
| 1.1 | Normalise all timestamps to UTC on input and in storage. Add a global exception handler that returns JSON and keeps CORS headers. | D-01, D-20 | POST aware and naive claims, then queue, forecast and context all return 200. |
| 1.2 | Load the CSV into `CLAIM_DATABASE` at startup. Compute rules, ML (fit on the full set) and centrality from the same claims. Remove the hardcoded centrality map. | D-02, D-16, D-24 | Queue lists ~200 providers with real centrality. |
| 1.3 | Stable case IDs mapped to providers, with `GET /api/v1/cases/{case_id}` detail (rule reasons, ML score, claims list). Return 404 for unknown IDs on context, graph, action, audit and brief. | D-04, D-12, D-13 | Unknown ID → 404. Known ID → detail with real claims. |
| 1.4 | Fix graph export: resolve the case to its provider, use one cached graph built at startup, use the correct label attribute, undirected neighbours. | D-05 | Different cases return different graphs with real labels. |
| 1.5 | Case status workflow: persist status, have `action` update it, and add `REFER_SIU` / `PAUSE_PAYMENT` actions. Persist the ledger (SQLite). | D-08, D-18 | Action → status changes → queue reflects it → restart keeps it. |
| 1.6 | Input validation (amount > 0, `claim_id` uniqueness, action enum in schema, length limits), typed response models on all endpoints. | D-14, D-23 | 422/409 on bad input. OpenAPI fully typed. |
| 1.7 | Add `GET /api/v1/stats` (KPIs), claims-by-case, provider profile and history, precedents (expose `HistoricalCaseMemory`), policy search. | D-12 | Each returns real aggregates. |
| 1.8 | Make `/analyze` return the composite risk too, and update the model and centrality inputs. Align `rule_flag_count` semantics. Add a phantom-billing rule and CPT benchmarks for CSV codes. | D-11, D-15 | Analysis matches the queue score for the same claim. |
| 1.9 | Make brief and chat consume real case context from the aggregator. Apply guardrails to briefs. Report `status` truthfully (`FALLBACK` vs `AI`). Add a Gemini timeout. | D-09, D-23, R-01, R-02 | Fallback is labelled. Case facts appear in output. |

### Phase 2 — Frontend wiring (UI unchanged, data real)

Do these in order, one at a time:

1. Remove the demo merge; gate demo data behind an explicit demo flag with a visible label. *(D-06)*
2. Surface backend `detail` messages. Add retry and reconnect for the connectivity check. *(D-21)*
3. Action dialog: remove fake success. Map every button to a real action. Update case status from the response. *(D-08)*
4. Audit Trail renders ledger entries (and exports them). Drop invented events. *(D-07)*
5. Analyzer renders the real response (flags, ML score, composite). *(D-11)*
6. Evidence matrix, rules and the "ML ANOMALY" gauge use real fields. *(F07)*
7. Linked claims, Provider page and KPIs use the new endpoints. *(F04, F10, F18)*
8. Fraud Network renders the real graph payload inside the existing SVG container. *(F11)*
9. Forecast tiles, chart and range tabs use `ExposureForecast`. Label the what-if model honestly. *(F12)*
10. Policy panel uses backend RAG results. Remove citations that are not in the corpus, or load them into the corpus. *(D-10)*
11. Copilot: send the typed message, history and real case context; render the actual reply, status and disclaimer. *(F16)*
12. Executive Brief renders `SIUBriefSchema` for the selected case; wire Copy. *(F17)*
13. Per-call timeouts (longer for LLM calls). *(R-02)*
14. Deep-Dive, global search, notifications: connect to the new endpoints or label as preview.

### Phase 3 — Verification

1. Make backend tests order-independent (`with TestClient(app)`, fixtures resetting state). Add contract tests for every endpoint and for D-01, D-04 and D-05 regressions. *(D-22)*
2. Add a Playwright smoke test covering login → queue → case → each tab → action → audit.
3. Re-run this audit's runtime probes and update the matrix.

### Phase 4 — Hardening

Authentication and server-side investigator identity, tightened CORS, prompt-injection hygiene, pinned dependencies, Docker and CI, router and component split of `App.tsx`. *(D-19, D-25, D-26)*

---

## 10. Highest-priority integration defects (summary)

1. **D-01** — A normal analyzer submission permanently breaks the queue, forecast and context endpoints (naive vs aware datetimes). Reproduced.
2. **D-02** — The "live" backend runs on 3 hardcoded claims, not the 4,950-claim dataset.
3. **D-03** — A non-placeholder Gemini API key is shipped inside the project zip. Rotate it.
4. **D-04 / D-05** — Unknown IDs silently return another case's data. The graph endpoint returns the same wrong graph for every case, and the UI draws a static picture anyway.
5. **D-06 / D-07 / D-08** — Demo rows are mixed with live rows. The audit trail shows invented events and hides real ones. "Refer to SIU" and "Pause payment" cannot work and fake-succeed offline.
6. **D-09 / D-10** — Copilot and Brief ignore all backend responses and user input, and the policy "citations" are not from the backend corpus.

**Next step:** confirm the five decisions in §9, then start Phase 0 and Phase 1, step 1.1 (the datetime crash), as a single change with its regression test.
