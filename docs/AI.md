# AI and recommendation architecture

## Default rule
The product must remain useful with AI_PROVIDER=none, no network access, and no API key. Deterministic Persian NLP and statistical insights are the fallback and must be tested.

## AIProvider contract
Use a small interface with complete(messages, options) and embed(texts, options). Provider selection uses AI_PROVIDER=none|openai_compatible|local and separately configurable base URL, model, key, timeout, retry, and circuit-breaker settings. Never hard-code a model or provider URL. Concrete network adapters belong to the feature phase that uses them.

## Safety and privacy
- Never send phone numbers, customer identities, OTPs, order verification codes, or direct identifiers to a model.
- Prefer catalog metadata and aggregated/anonymized behavior.
- Validate structured provider output against Pydantic schemas.
- Use bounded timeouts/retries, circuit breaking, and deterministic fallback.
- Treat model output as untrusted suggestions, not commands.
- AI must never directly alter products, prices, discounts, published combos, study rules, or rewards.
- Merchant approval/rejection is explicit and audited.

## Smart Combo
The ranking service combines sales velocity, margin, co-occurrence, time of day, and current cart context. Keep scoring explainable and testable. BOOST_BESTSELLER and PUSH_SLOW_MOVER are explicit strategies. No unapproved combo is customer-visible.

## Persian natural-language search
Normalize Persian/Arabic Yeh and Kaf, half-spaces, digits, spelling variants, and synonyms; rank only real available catalog products; explain each result. Ambiguous or unsupported requests return a clarification prompt instead of a random recommendation. Models cannot invent products or allergens.

## Prompts
Store prompts as versioned files under backend/app/prompts/ in the phase that first needs them. Do not put prompts inline in route handlers and do not log personal data.
