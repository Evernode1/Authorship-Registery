# Original Authorship Registry

A GenLayer intelligent contract that settles "who published this first?" on-chain.

An author registers the URL of a post, thread, article, repo or video and locks a small bond.
If someone believes that work copies *their earlier* content, they open a dispute with their own
earlier URL and a larger stake. GenLayer validators fetch both pages (and any defense evidence),
report a few categorical facts, and the contract's own code decides who was first. The winner holds
the on-chain **first-author** record. A false challenger loses their stake, and an upheld challenge
slashes the copier's bond.

```
register_work ─► ACTIVE ─► open_dispute ─► UNDER_DISPUTE ─► resolve_dispute ─┬─► UPHELD        challenger holds first-author record
   (bond)          │          (stake)          │                              ├─► REJECTED      author keeps it, challenger forfeits stake
                   │                           └─► respond_to_dispute         └─► INCONCLUSIVE  retry (max 3), then stake back minus a fee
                   └─► verify_work_ownership (optional proof that the author controls the page)
```

## Who decides what

The model never gives a verdict. Validators only report facts, and `_decide` (plain contract code)
applies the rules:

| Validators report | Contract decides |
| --- | --- |
| `similarity`: IDENTICAL / SUBSTANTIALLY_SIMILAR / DIFFERENT / UNDETERMINED | DIFFERENT means the challenge is **rejected** |
| whether the challenger's page carries the challenger's proof token | missing proof means **inconclusive** |
| publication dates of the challenger's page, the registered page, and optional defense evidence | challenger must be earlier by at least 1 hour to win; later by 1 hour or more loses; in between is inconclusive |
| whether the defense evidence is the same content as the registered page | only `SAME_CONTENT` evidence can move the author's date earlier |

Safeguards built into this split:

- **Burden of proof is on the challenger.** Missing proof, unreadable pages, unknown or implausible dates and near-ties never win a dispute.
- **Proof of control.** A challenger must put `oar-proof:<their address, lowercase>` on their page (`get_expected_proof`). Without it nobody could "challenge" with someone else's famous old URL.
- **No model text is stored.** Rationales are built in code from fixed outcome codes, and dates are stored only if they parse as sane calendar dates (after 1991, not in the future). A hostile page has no channel to push text on-chain through the model.
- **Unknown model values fall back safely** (to `UNDETERMINED` / `FETCH_UNAVAILABLE`), never to a win.
- **No re-litigation.** A challenger who loses on the merits cannot dispute the same work again.

## Money

All payouts are pull-payments (`withdraw()`); nothing is transferred inside a consensus path.

| Event | Flow |
| --- | --- |
| `register_work` | bond of at least 0.001 GEN locked on the work |
| `open_dispute` | stake of at least 0.005 GEN locked (larger than the bond, so attacking costs more than registering) |
| **UPHELD** | challenger gets stake back plus 50% of the author's bond; rest of the bond goes to the reward pool |
| **REJECTED** | author gets 60% of the stake as compensation; rest goes to the pool |
| 3rd inconclusive round | dispute closes, challenger gets stake back minus 10% (to the pool) |
| `withdraw_dispute` | stake back minus 10% fee (so "open a dispute to freeze a work, then leave" isn't free) |
| `release_bond` | author's bond back once the 180 day challenge window has passed, if the work is active or withdrawn (so a bond can't be pulled out while a dispute is still possible) |
| rewards | 0.0005 GEN from the pool to whoever triggers a successful ownership check or a decisive (UPHELD/REJECTED) resolution; nothing for undecided rounds |

`get_accounting()` exposes the invariant `pool + bonds + stakes + pending == deposited - withdrawn`
as `balanced`.

## Timing

| Window | Length |
| --- | --- |
| Author's response window after a dispute opens | 3 days (resolution can happen earlier once the author has responded) |
| Challenge window after registration | 180 days |
| Bond lock | 180 days (same as the challenge window) |
| Cooldown between ownership checks / between resolution rounds | 1 day |

## Using it

1. Deploy `contracts/AuthorshipRegistry.py` on GenLayer Studio (the deployer becomes admin).
2. **Register:** call `register_work(url, title, content_type, fingerprint)` with at least 0.001 GEN attached. `content_type` is one of `POST, THREAD, ARTICLE, REPO, VIDEO, OTHER`. `fingerprint` is optional (empty or a sha256 hex of your content; informational only).
3. **Prove control (optional):** put the text from `get_expected_proof(your_address)` on the page, then call `verify_work_ownership(work_id)`.
4. **Challenge:** put *your* proof token on your earlier page, then call `open_dispute(work_id, your_url, statement)` with at least 0.005 GEN.
5. **Defend:** the author calls `respond_to_dispute(dispute_id, evidence_url, statement)`, ideally with an archive snapshot that predates the challenger.
6. **Resolve:** after the response window (or once the author has responded), anyone calls `resolve_dispute(dispute_id)`.
7. **Look up:** `get_first_author(url)` returns the current first-author, following any overturned registrations (`chain`).

URLs are canonicalized so one piece of content has one key: https, no `www.`, `twitter.com` folded
into `x.com`, tracking parameters and fragments dropped, trailing slashes removed. Caller-supplied
URLs must be public domain names (no IP literals, credentials, odd ports, local hosts or URL
shorteners). Archive URLs keep their embedded `https://`.

Full method list, storage schema and outcome codes are in [ARTIFACT.md](ARTIFACT.md). Design
reasoning and rejected alternatives are in [DECISION.md](DECISION.md).

## Admin (deliberately narrow)

The admin can blacklist or reinstate an address and transfer the admin role. A blacklisted address
cannot register, dispute, or have ownership checks run. It **can** still respond to a dispute
already opened against it. The admin cannot change outcomes, edit records, or move funds.

## Tests

```
pip install -r requirements.txt
pytest tests/direct -v      # integration tests, genlayer-test direct mode
pytest tests/unit -v        # pure helpers, plain pytest (no genlayer-test needed)
```

- `tests/unit/test_pure_logic.py`: URL canonicalization and rejection, date parsing, the full ruling table (`_decide`) including gap boundaries and evidence handling, fingerprint and constant checks. It stubs the `genlayer` package just long enough to import the contract.
- `tests/direct/test_authorship_registry.py`: the whole lifecycle with `mock_web` and `mock_llm` pinning every consensus round: registration validation, ownership checks and keeper rewards, opening/responding/withdrawing disputes, UPHELD / REJECTED / every INCONCLUSIVE path, the 3-round close, money flows and the accounting invariant, injection safety, pagination, admin rules.

Status when this was written: the unit tests pass (68 cases), and the contract's state machine was
exercised separately against dict-backed storage with canned consensus results (all flows and the
accounting invariant held). The `tests/direct` suite could not be run in that environment (no
network, so `genlayer-test` could not be installed). Run it once locally and fix any harness-level
differences, for example how an unreachable page behaves under `mock_web`.

## Honest limitations

- Dates are what pages say. A page can claim any date in its own body. Validators prefer machine-readable metadata and platform timestamps, and defenders can bring archive snapshots, but this is evidence, not cryptographic proof.
- "Similarity" is a model judgment. Paraphrase and translation are genuinely hard and often land on `UNDETERMINED`, which is safe (inconclusive) but unhelpful.
- First to **publish** wins, not first to register. Registration time is used only when the registered page shows no readable date.
- Caller-supplied URLs are fetched. Shape checks are strict, but DNS rebinding and server-side redirects to private hosts are not defended in the contract; the validators' network sandbox is the backstop.
- A page that changes after a check is not re-examined unless someone disputes.
- This means "first publisher of this content as read from the web", not legal copyright ownership.
