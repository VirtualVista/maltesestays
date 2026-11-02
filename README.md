# Maltese Stays (maltesestays.com)

Guest-facing direct booking website for Landlord Care, Malta. Static HTML generated from the Boom booking engine.

- `build.py` reads the public Boom listings API, merges it with the hand-written copy in `data/listings.json`, and writes the site to `dist/`.
- A GitHub Action rebuilds and publishes the site every day at 04:17 UTC, on every push, and when you press "Run workflow". New listings in Boom appear automatically with their Boom text; listings removed from Boom disappear.
- `data/listings.json`: hand-written copy per Boom listing id. Add an entry to replace the automatic text for a new property.
- `data/areas.json`, `data/groups.json`: area guides and guest house pages.
- `BOOK_BASE` in `build.py`: the Boom engine domain (switch to `https://book.maltesestays.com` once the CNAME is live).

Local build: `python3 build.py` (needs internet to reach Boom; falls back to the curated list).
