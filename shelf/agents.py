"""The SHELF agent crew, on Google ADK.

CURATOR    sees each item photo (Gemini vision): what it is, condition, flaws.
APPRAISER  price-comps with cited sources; abstains rather than invents.
COPYWRITER writes the honest listing in the seller's voice.
(SHOPKEEPER and BOOKKEEPER live in storefront/ and ledger/ - M2.)

Design law inherited from the builder's own selling practice: flaws are DISCLOSED
as a feature, comps carry receipts, and a human approves before anything goes live.
"""
from google.adk.agents import LlmAgent, SequentialAgent
from shelf.tools import comps_search

GEMINI = "gemini-3.5-flash-lite"  # rules: Gemini 3.5 or newer. LITE because flash free tier = 20 req/DAY (killed the 8/18 feed); lite tier is the volume lane. Do not switch back to bare flash without checking ai.google.dev rate limits.

curator = LlmAgent(
    name="curator",
    model=GEMINI,
    description="Identifies an item from photos: name, category, condition, flaws.",
    instruction=(
        "You are the CURATOR for a personal storefront. You receive one or more "
        "photos of a single item someone wants to sell. Report, as JSON: "
        "item_name (specific, include brand/model if visible), category, "
        "condition ('new'|'like_new'|'good'|'fair'|'poor'), condition_notes, "
        "visible_flaws (list, empty if none - NEVER hide a flaw), "
        "key_attributes (size, color, material when visible), confidence (0-1), "
        "hero_index (0-based index of the photo that best SELLS the item on a "
        "storefront card: the artwork or front face fully visible and dominant. "
        "NEVER pick a photo showing the back, hanging hardware, packaging, or "
        "sleeve when any front/art view exists). "
        "If you cannot identify the item, say so plainly in item_name. "
        "NEVER name a real artist, musician, album, brand, movie, or franchise "
        "in item_name or anywhere else - describe only what is visually present "
        "(a wrong attribution on a public store is fraud risk)."
    ),
)

appraiser = LlmAgent(
    name="appraiser",
    model=GEMINI,
    description="Prices the item from comparable listings, with cited sources.",
    instruction=(
        "You are the APPRAISER. Given the curator's item report and web search "
        "results for comparable prices, produce JSON: new_price_estimate, "
        "used_range_low, used_range_high, suggested_list, suggested_floor, "
        "comps (list of {source_url, price, note}). RULES: every number must trace "
        "to a comp in your list. If search results are insufficient, return "
        "needs_human_pricing=true instead of inventing numbers. Use your "
        "comps_search tool to find current comparable prices before answering."
    ),
    tools=[comps_search],
)

copywriter = LlmAgent(
    name="copywriter",
    model=GEMINI,
    description="Writes the honest, plain-text listing.",
    instruction=(
        "You are the COPYWRITER. From the curator and appraiser reports, write "
        "the listing: title (under 80 chars, no hype words), "
        "description (plain text, warm but honest, discloses every flaw the "
        "curator found, states dimensions/attributes, ends with pickup/shipping "
        "line), tags (10 search keywords). Plain text only - no markdown symbols."
    ),
)

item_crew = SequentialAgent(
    name="shelf_item_crew",
    description="Runs one item from photos to a draft listing.",
    sub_agents=[curator, appraiser, copywriter],
)
