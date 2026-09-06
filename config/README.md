# config/

| File | What |
|---|---|
| `desk-profile.json` | the shared rule set two operators run their own desks against, so both admit the same names |

The profile exists so a desk's admitted universe is a **declared** object
rather than an accident of each machine's `.env`. An `.env` override still
wins, and the override is recorded in the desk fingerprint rather than hidden
— see `scripts/desk_parity.py`.
