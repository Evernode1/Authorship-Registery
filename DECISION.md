# Design decisions

Why the contract is shaped the way it is, what was considered, and what was knowingly accepted.

## 1. The model extracts facts; code rules

**Decision.** Validators report `similarity`, a proof-token flag, and up to three publication dates.
The ruling (`_decide`) is plain code over those normalized values.

**Why.** An authorship ruling moves money. A single holistic "who wins?" answer from a model is
hard to audit, easy to steer with hostile page text, and hard to make validators agree on. Facts
with small closed vocabularies (or calendar days) are far easier to reach consensus on, and the
rules become readable and testable (`tests/unit` exercises the whole table).

**Rejected.** "Ask the model who the original author is." It is shorter and fails exactly where it
matters: an attacker's page can contain instruction-like text, and nobody can say why it ruled that way.

## 2. Burden of proof sits on the challenger

**Decision.** Only an explicit, provable earlier publication upholds a challenge. Missing proof
token, unreadable page, unknown/implausible date, undetermined similarity and near-ties are all
INCONCLUSIVE. The challenger also has to be earlier by at least one hour.

**Why.** The registered author is the status quo; a challenge is a request to take something away.
Defaulting uncertainty toward the registered author protects honest authors from griefing.
INCONCLUSIVE is not a loss for anyone: retries are allowed, and after three rounds the stake comes
back minus a small fee.

**Cost accepted.** A genuine original whose page has no readable date cannot win. They need a page
or archive snapshot that exposes a date.

## 3. Challenger proof token

**Decision.** The challenger's earlier page must contain `oar-proof:<their address>`.

**Why.** Without it anyone could point at a famous old URL they don't control and claim to be its
author. The token ties the claim to the wallet that staked. It is the same idea as the bio-address
proof in Contribution Attestor, applied to arbitrary pages.

## 4. Dates: sanity-filtered, epoch-compared, fallback to registration time

**Decision.** Every model-reported date is parsed deterministically and discarded unless it is
after 1991-01-01 and not more than a day in the future. Comparisons use UTC epoch seconds. If the
registered side shows no readable date at all, the registration timestamp is the fallback.

**Why.** Dates are the one number a hostile page can try to fake ("published 1999"). A sane-range
filter removes the cheapest attacks, and epoch comparison removes dependence on string formats.
The fallback means a work whose page shows no date is judged by when the claim was made, which is
the latest it could have existed.

**Cost accepted.** A page can still lie within the sane range. That is a limit of any web-read
approach and is documented, not hidden.

## 5. Defense evidence only counts when it is the same content

**Decision.** The author may add one evidence URL (typically an archive snapshot or earlier post).
Its date only lowers the author's date if validators report `SAME_CONTENT`.

**Why.** Otherwise an author could attach any old page to push their date back. Only evidence
that shows the *same* content earlier is relevant. The earliest usable date among the page and the
evidence is used.

## 6. Two stakes, and the stake is larger than the bond

**Decision.** Registration needs a bond (0.001 GEN); a challenge needs a stake (0.005 GEN).

**Why.** Registration should be cheap so honest authors use it. Attacking should cost more than
registering, because a challenge freezes the work. The bond is also what an upheld challenge slashes,
so copiers pay for what they registered.

## 7. Where the money goes

The bond stays locked for the whole 180 day challenge window. A shorter lock would let a copier
register, wait, and pull the bond out while the work is still challengeable, leaving nothing to
slash and no bounty for the challenger who exposes them. The bond is small (0.001 GEN), so locking
it for the window is cheap for honest authors.

- **UPHELD:** challenger gets stake back and half the bond; the other half feeds the pool. The
  half-bond bounty rewards challenges without making a challenge profitable to fabricate against
  yourself (the "victim" bond is your own).
- **REJECTED:** author gets 60% of the stake as compensation for being frozen; 40% to the pool.
- **Withdraw / third inconclusive round:** stake minus 10% fee to the pool, so freezing a work and
  leaving costs something.
- **Rewards** (0.0005 GEN) go to whoever triggers a successful ownership check or a *decisive*
  resolution, and never for undecided rounds, so nobody profits from triggering rounds that
  decide nothing. A decisive outcome feeds the pool at least as much as the reward (half the bond
  when upheld, 40% of the stake when rejected, at the minimum amounts), and rewards are skipped
  silently if the pool cannot pay, so they can never block an outcome.

## 8. Pull payments and an accounting invariant

**Decision.** Outcomes only credit internal balances. `withdraw()` pays out. `get_accounting()`
exposes pool, bonds, stakes, pending, deposits, withdrawals and whether they balance.

**Why.** No transfer inside a consensus path means a failing or malicious recipient can never
block a resolution. The invariant makes the contract's solvency checkable by anyone.

## 9. URLs are canonicalized and strictly shaped

**Decision.** One canonical key per content (https, no `www.`, twitter folded to x.com, tracking
parameters/fragments dropped, trailing slashes removed, query sorted, X and GitHub paths
lowercased). Archive hosts keep `//` inside the path. Only domain names are accepted (no IP
literals in any encoding, credentials, non-standard ports, local suffixes or URL shorteners). `@`
is allowed in the path because Medium uses `/@author/...`.

**Why.** Without canonicalization one post can be registered many times under cosmetic variants,
which is the easiest way to defeat first-registrant logic. The strict shape rules reduce what
validators are asked to fetch, since all of these URLs are caller-supplied.

**Cost accepted.** Canonicalization is syntactic. It cannot know that two different domains mirror
the same content, and it does not follow redirects.

## 10. Priority is tracked as a chain, not an overwrite

**Decision.** An upheld challenge marks the old work OVERTURNED and points `superseded_by` at the
winner (a new work created for the challenger, or the challenger's own earlier registration of
that URL). `get_first_author(url)` follows the chain.

**Why.** History stays auditable; nothing is silently rewritten. A challenger who already
registered their URL simply inherits priority, with their own bond untouched.

## 11. Blacklist is narrow, and never silences a defendant

**Decision.** The admin can blacklist/reinstate and hand over the role. Nothing else. A
blacklisted address cannot register, dispute or have ownership checked, but can still respond to
an open dispute.

**Why.** Some moderation power is needed against spam, but power over outcomes or funds would
undercut the point of an on-chain registry. Allowing the defense even when blacklisted removes the
one way an admin could tilt an open case without touching the ruling logic.

## 12. Not built, on purpose

- **Admin overrides of outcomes or funds.** Any such power makes every ruling revocable.
- **Automatic discovery of copies.** The contract adjudicates disputes someone brings; scanning the
  web for plagiarism is a different, much larger system.
- **Content stored on-chain.** Only URLs, a canonical key, an optional fingerprint and short fixed
  text are stored.
- **Appeals.** A rejected challenger cannot re-litigate the same work. Nothing else is appealable
  as such: an overturned author who has new evidence can open an ordinary new dispute against the
  winner's registration. A multi-level appeal process would need a different trust model.
- **Verifying the optional fingerprint.** It is informational; contracts cannot hash a web page.
