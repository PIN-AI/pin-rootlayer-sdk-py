# RootLayer HTTP

This SDK supports the following HTTP endpoints (from `rootlayer/api/rootlayer/service.proto`):

- `GET  /health` (`HealthService.Check`)
- `POST /api/v1/intents/submit` (`SubmitIntent`)
- `POST /api/v1/intents/submit/batch` (`SubmitIntentBatch`)
- `GET  /api/v1/intents/query` (`GetIntents`)
- `GET  /api/v1/intents/query/{intent_id}` (`GetIntent`)
- `POST /api/v1/callbacks/assignment/submit` (`PostAssignment`)
- `POST /api/v1/callbacks/assignments/submit` (`PostAssignmentBatch`)
- `POST /v1/direct/intents` (`SubmitDirectIntent`)

## Bytes fields

Protobuf JSON mapping uses base64 for `bytes`. The SDK accepts:

- `bytes`
- base64 string
- `0x` hex string

When sending HTTP requests, the SDK serializes `bytes` to base64.
