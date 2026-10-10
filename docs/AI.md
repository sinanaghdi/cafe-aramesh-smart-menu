# AI and recommendation architecture

## Default rule
The product must remain useful with AI_PROVIDER=none, no network access, and no API key. Deterministic Persian NLP and statistical insights are the fallback and must be tested.

## AIProvider contract
The Python Protocol is defined at backend/app/services/ai/provider.py with complete(messages, options) and embed(texts, options). Provider selection is typed/configured by AI_PROVIDER=none|openai_compatible|local; base URL, model, API key, and timeout are separate settings. Phase 0 deliberately provides the interface and configuration only; provider network adapters and their resilience/fallback orchestration belong to the phase that first consumes them. No external provider is required to start the app.

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

## Future extension flags
FEATURE_ONLINE_ORDERING_ENABLED, FEATURE_AI_AGENT_ENABLED, and FEATURE_AI_SUPPORT_ENABLED default to false. They are reserved switches, not permission to expose unimplemented features. Do not build these capabilities inside the MVP phases above.

## Prompts
Store prompts as versioned files under backend/app/prompts/ in the phase that first needs them. Do not put prompts inline in route handlers and do not log personal data.
