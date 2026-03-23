---
sidebar_position: 0
---

# Conlyse Documentation

Conlyse is an unofficial full-stack system for recording, storing, and analyzing Conflict of Nations games.
It consists of an end-to-end replay pipeline (Observer -> Converter -> storage -> API) plus the `ConflictInterface` library that powers time-travel replay playback.


If you're deploying the full stack, follow the **Deployment** guide first:

- [User Guide: Deployment](./user-guide/deployment)

If you want the operational details for the services that make up the pipeline, see:

- [User Guide: Server Observer](./user-guide/services/server-observer)
- [User Guide: Server Converter](./user-guide/services/server-converter)

If you're working on the replay and parsing internals, start with:

- [Developer Guide: Replay System](./developer-guide/libraries/conflict-interface/replay-system)
- [Developer Guide: Data Types](./developer-guide/libraries/conflict-interface/data-types)
