# Categorize

Predicts a category for a transaction, and learns from user corrections.

## How it works

Three tiers run in order.

1. Rules: User regex -> category
2. Memory (exact): Merchant key -> category counts
3. Memory (compact): Same key ignoring spaces
4. Memory (subset): IDF-weighted tokens, typo correction.
5. None

```
SQ *BLUE BOTTLE 04412 CHICAGO IL -> blue bottle
BLUE BOTTLE COFFEE #A12QX9       -> blue bottle coffee
SHELL OIL #087C70              -> shell oil
```

### Subset matching

When no key matches exactly, a stored key whose tokens are a subset (or
superset) of the query's is used instead, so a partially renamed merchant still
resolves:

```
"Starbucks Coffee"  -> starbucks       -> Coffee Shops 0.78
"Shell Gas Station" -> gas station     -> Gas & Fuel   0.53
"Thai"              -> thai restaurant -> Restaurants  0.55
```

### Typo tolerance

Tokens that aren't known are resolved to the closest one that is, before subset matching runs.

```
"Starbcuks"     -> starbucks     -> Coffee Shops 0.63
"Groceyr Store" -> grocery store -> Groceries    0.61
"Chrunchy roll" -> crunchy roll  -> Television   0.58
```