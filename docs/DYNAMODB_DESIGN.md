# DynamoDB design (single table)

Access patterns first, keys second. These are the only questions the application asks storage.

| # | Question | Who asks | How DynamoDB answers |
|---|---|---|---|
| AP1 | Load one conversation | every customer reply | `GetItem PK=CONV#<id>, SK=STATE` (consistent read) |
| AP2 | All tickets for a brand | dashboard | `Query PK=BRAND#<brand>, SK begins_with TICKET#` |
| AP3 | One ticket by id | staff changing a ticket's status | `Query GSI1 GSI1PK=TICKET#<id>` |
| AP4 | The next ticket number | escalation | `UpdateItem PK=CTR, SK=TICKET  ADD n :1  ReturnValues=UPDATED_NEW` (atomic) |
| AP5 | Earlier cases for a serial in a time window | recurrence check when OpenSearch is unreachable | `Query GSI1 GSI1PK=SERIAL#<serial>, GSI1SK >= CASE#<iso cutoff>` |
| AP6 | Every case for a brand | brand insights when OpenSearch is unreachable | `Query PK=BRAND#<brand>, SK begins_with CASE#` |
| AP7 | Wipe demo data | demo reset only | `Scan` + `DeleteItem` (never on a request path) |

## Items

| item | PK | SK | GSI1PK | GSI1SK |
|---|---|---|---|---|
| conversation (whole state as one JSON attribute, `ttl` = 7 days) | `CONV#<id>` | `STATE` | | |
| ticket | `BRAND#<brand>` | `TICKET#<id>` | `TICKET#<id>` | `BRAND#<brand>` |
| case | `BRAND#<brand>` | `CASE#<iso>#<conv id>` | `SERIAL#<serial>` | `CASE#<iso>` |
| ticket counter | `CTR` | `TICKET` | | |

## Why these choices
- **One table, one overloaded GSI.** Brand is the natural tenant boundary, so it leads the partition key for tickets and cases (AP2, AP6). GSI1 is overloaded: it means "by ticket id" for tickets and "by serial" for cases, because no item needs both.
- **ISO timestamps in the sort key** sort chronologically as strings, which makes the recurrence window (AP5) a plain range condition.
- **Atomic counter** (AP4): `ADD` returns the new value in the same call, so two escalations at once can never draw the same id. The file store's `len(files)+1` could. This is why ticket ids moved off files.
- **Conversation as one JSON attribute.** It is only ever read and written whole, so splitting it into attributes would buy nothing and add write cost.
- **TTL** on conversations (`ttl`) and on the idempotency table (`expiration`) means expiry costs nothing to run.
- **Idempotency table** is separate because Lambda Powertools owns its schema (`id` hash key); it stores each `Idempotency-Key`'s result for 60 s so a retried `POST /api/start` returns the same conversation instead of opening a second one and a second ticket.

## Local vs cloud
`DYNAMODB_ENDPOINT` points boto3 at DynamoDB Local; unset it and the same code talks to DynamoDB. `template.yaml` declares both tables, so `sam deploy` would create them; locally `scripts/bootstrap_local.py` creates them in DynamoDB Local, reading the definitions from `template.yaml` so the two cannot drift. The application never creates a table.
