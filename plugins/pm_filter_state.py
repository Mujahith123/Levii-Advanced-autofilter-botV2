"""
Shared in-memory state for the pm_filter / pm_filter_search split.

pm_filter.py (handlers: search results pagination, quality/year/language/
season refinement, the general callback dispatcher) and pm_filter_search.py
(auto_filter / manual_filters / global_filters / advantage_spell_chok — the
search + custom-filter engine) both read and write these dicts to pass
search state between a message handler and the callback buttons it sends.

This was originally a set of module-level globals inside pm_filter.py.
Moving them here — and having both files import the *same* objects from
this one module — keeps that exact behavior: Python caches modules, so
every importer gets the same dict instances, and mutations made in one
file are visible in the other immediately, exactly as before the split.

Do not import this module's contents by value (e.g. copying a dict) —
always mutate the imported names in place, as the existing code already
does (e.g. `FRESH[key] = search`, `PAGE_CACHE.pop(ck, None)`).
"""
import asyncio

# Guards the delete-by-keyword admin operation (killfilesdq) in pm_filter.py
# so concurrent admin clicks don't race on the same bulk delete.
lock = asyncio.Lock()

# BUTTON and CAP are unused beyond this initialization in the original code
# (no reads/writes elsewhere) — kept only so nothing that referenced them
# (even speculatively) breaks.
BUTTON = {}
CAP = {}

# key -> refined search string (set when a quality/year/language filter is
# applied on top of the original search). Read by next_page and the *_cb_handler
# pairs in pm_filter.py; written by those same handlers and cleared back to the
# original search when "homepage" is selected.
BUTTONS = {}

# key -> original/base search string for a given results message. Written by
# auto_filter when results are first shown; read throughout pm_filter.py to
# restore the unfiltered query.
FRESH = {}

# key -> season-filtered search variants (3 candidate season-number formats
# tried by filter_seasons_cb_handler). Read in cb_handler's sendfiles branches.
BUTTONS0 = {}
BUTTONS1 = {}
BUTTONS2 = {}

# message_id -> list of candidate movie titles offered by the spell-checker.
# Written by advantage_spell_chok; read by advantage_spoll_choker when the
# user taps one of the suggested titles.
SPELL_CHECK = {}

# (search_key, offset) -> {"btn": [...], "cap": str_or_None}
# Per-page button/caption cache so BACK restores the exact original layout
# in PM text-filter mode. Written and read across next_page and the
# quality/year/language/season filter handlers.
PAGE_CACHE = {}
