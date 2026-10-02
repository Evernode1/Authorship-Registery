# AuthorshipRegistry: contract artifact

Reference sheet for integrators: interface, storage schema, constants, outcome codes and deployment.
Contract file: `contracts/AuthorshipRegistry.py` (class `AuthorshipRegistry`, GenLayer Python).

## Deployment

| Item | Value |
| --- | --- |
| Constructor arguments | none |
| Admin | the deploying address |
| Dependency header | `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` |
| Networks | GenLayer Studio / localnet (see `gltest.config.yaml`) |
| Deployed address | _fill in after deploying_ |
| Explorer link | _fill in after deploying_ |

After deploying, a quick smoke test: call `get_config()`, then `get_registry_stats()` (all zeros).

## Constants

| Name | Value |
| --- | --- |
| Registration bond | 0.001 GEN (`10**15` wei) minimum |
| Challenge stake | 0.005 GEN (`5 * 10**15` wei) minimum |
| Keeper reward (successful ownership check) | 0.0005 GEN |
| Resolver reward (UPHELD / REJECTED round) | 0.0005 GEN |
| Author share of a forfeited stake | 60% |
| Challenger bounty from a slashed bond | 50% |
| Fee on withdrawn dispute / on closing after inconclusive rounds | 10% of stake |
| Response window | 3 days |
| Challenge window | 180 days from registration |
| Bond lock | 180 days (= challenge window) |
| Ownership recheck cooldown / resolution cooldown | 1 day |
| Max resolution rounds | 3 |
| Minimum priority gap | 1 hour |
| Dates accepted | after 1991-01-01, at most 1 day in the future |
| Field limits | title 1-120, statement 10-500, URL 10-300, page size max 50 |

`get_config()` returns all of these at runtime.

## Write methods

| Method | Who | Payable | Notes |
| --- | --- | --- | --- |
| `register_work(url, title, content_type, fingerprint)` | anyone | bond (min 0.001 GEN) | one record per canonical URL; `content_type` in POST, THREAD, ARTICLE, REPO, VIDEO, OTHER; `fingerprint` empty or sha256 hex |
| `withdraw_registration(work_id)` | author | no | frees the URL; not allowed while disputed; bond stays locked |
| `release_bond(work_id)` | author | no | after the 180 day lock, for ACTIVE or WITHDRAWN works; credits the balance |
| `verify_work_ownership(work_id)` | anyone | no | consensus round; page must contain the author's proof token; cooldown 1 day; keeper reward on success |
| `open_dispute(work_id, challenger_url, statement)` | anyone except the author | stake (min 0.005 GEN) | one open dispute per work; challenger URL must differ and must not belong to another address |
| `respond_to_dispute(dispute_id, evidence_url, statement)` | author | no | once, within the response window; evidence URL optional |
| `withdraw_dispute(dispute_id)` | challenger | no | refund minus 10% fee |
| `resolve_dispute(dispute_id)` | anyone | no | consensus round; after the response window or once the author has responded |
| `fund_rewards()` | anyone | any amount > 0 | adds to the reward pool |
| `withdraw()` | anyone | no | pays out the caller's balance |
| `blacklist_address(target, reason)` | admin | no | reason 3-300 characters |
| `unblacklist_address(target)` | admin | no | |
| `transfer_admin(new_admin)` | admin | no | zero address refused |

## View methods

| Method | Returns |
| --- | --- |
| `get_work(work_id)` / `get_work_by_url(url)` | work record, or `{}` |
| `get_first_author(url)` | current first author following overturned works: `first_author`, `first_work_id`, `chain`, `overturned`, `status`, `ownership` |
| `list_works(offset, limit)` / `list_works_by_author(author, offset, limit)` | work records (limit capped at 50) |
| `get_dispute(dispute_id)` | dispute record, or `{}` |
| `list_disputes(offset, limit)` / `list_disputes_for_work(work_id)` / `list_disputes_by_challenger(addr)` | dispute records |
| `get_author_stats(address)` | `works_registered`, `works_overturned`, `defenses_survived`, `disputes_opened`, `disputes_upheld`, `disputes_rejected` |
| `get_balance(address)` / `get_reward_pool()` | wei as decimal strings |
| `get_accounting()` | `reward_pool`, `locked_bonds`, `open_stakes`, `pending_withdrawals`, `total_deposited`, `total_withdrawn`, `balanced` |
| `get_expected_proof(address)` | `oar-proof:<address lowercase>` |
| `preview_canonical_url(url)` | the canonical key a URL would be stored under |
| `get_registry_stats()` | `total_works`, `total_disputes`, `disputes_upheld`, `disputes_rejected` |
| `get_config()` | constants above |
| `get_admin()` / `get_blacklist_status(address)` | admin address / `{blacklisted, reason}` |

## Records

**Work:** `work_id, url, original_url, title, content_type, author, fingerprint, status, ownership,
ownership_result, page_published_at, ownership_attempts, ownership_checked_at, bond, registered_at,
challenge_window_closes_at, superseded_by, active_dispute, disputes_survived, origin_dispute,
author_blacklisted`

**Dispute:** `dispute_id, work_id, challenger, challenger_url, statement, stake, status, opened_at,
response_deadline, responded, evidence_url, respondent_statement, responded_at, attempts,
last_checked_at, outcome_code, similarity, challenger_page_status, evidence_status,
challenger_published_at, respondent_published_at, evidence_published_at, rationale, resolved_at,
resulting_work`

Amounts are decimal strings of wei; ids, counts and booleans are native JSON types.

## Statuses

| Field | Values |
| --- | --- |
| Work `status` | `ACTIVE`, `UNDER_DISPUTE`, `OVERTURNED`, `WITHDRAWN` |
| Work `ownership` | `UNVERIFIED`, `VERIFIED` |
| Work `ownership_result` | `PROOF_FOUND`, `PROOF_NOT_FOUND`, `FETCH_UNAVAILABLE`, `""` |
| Dispute `status` | `OPEN`, `UPHELD`, `REJECTED`, `CLOSED_INCONCLUSIVE`, `WITHDRAWN` |
| `similarity` | `IDENTICAL`, `SUBSTANTIALLY_SIMILAR`, `DIFFERENT`, `UNDETERMINED` |
| `challenger_page_status` | `ADDRESS_FOUND`, `ADDRESS_NOT_FOUND`, `NOT_CHECKED` (registered page failed first), `FETCH_UNAVAILABLE` |
| `evidence_status` | `NOT_PROVIDED`, `SAME_CONTENT`, `DIFFERENT`, `FETCH_UNAVAILABLE` |

## Outcome codes (`outcome_code`, with the fixed `rationale` text stored for each)

| Code | Verdict | Meaning |
| --- | --- | --- |
| `CHALLENGER_FIRST` | UPHELD | same content, challenger published at least 1 hour earlier |
| `CHALLENGER_PUBLISHED_LATER` | REJECTED | same content, challenger is not earlier |
| `CONTENT_DIFFERENT` | REJECTED | the pages are different content |
| `FETCH_UNAVAILABLE` | INCONCLUSIVE | a required page could not be fetched |
| `SIMILARITY_UNDETERMINED` | INCONCLUSIVE | similarity could not be determined |
| `CHALLENGER_PROOF_MISSING` | INCONCLUSIVE | challenger's proof token not on their page |
| `CHALLENGER_DATE_UNKNOWN` | INCONCLUSIVE | no usable publication date for the challenger's page |
| `TOO_CLOSE_TO_CALL` | INCONCLUSIVE | both dates within the 1 hour gap |
| `CHALLENGER_URL_TAKEN` | INCONCLUSIVE | challenger's URL was registered by another address meanwhile |

## Errors

User-facing reverts are prefixed `[EXPECTED]` (bad input, wrong state, cooldowns). A model that
returns non-JSON raises `[LLM_ERROR]`; the transaction fails and can be retried.

## Example calls (genlayer-js)

```ts
// register (0.001 GEN bond)
await client.writeContract({
  address, functionName: "register_work",
  args: ["https://medium.com/@me/my-essay", "My essay", "ARTICLE", ""],
  value: 10n ** 15n,
});

// challenge (0.005 GEN stake), after putting get_expected_proof(me) on the earlier page
await client.writeContract({
  address, functionName: "open_dispute",
  args: [1, "https://myblog.dev/first-draft", "I published this on my own blog in March."],
  value: 5n * 10n ** 15n,
});

// who is first?
await client.readContract({ address, functionName: "get_first_author", args: ["https://x.com/me/status/123"] });
```
