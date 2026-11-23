# UML Sequence Diagram — Perubahan Jadwal (Minggu 8)

Diagram menggambarkan kode `SchedulingService`, `KRSInvalidator`, outbox dan dispatcher.

```mermaid
sequenceDiagram
    actor Admin
    participant API as FastAPI
    participant Service as SchedulingService
    participant DB as Database
    participant Inv as KRSInvalidator
    participant Disp as OutboxDispatcher
    participant Subject as ScheduleSubject
    participant Obs as Student/Lecturer/Admin Observer
    participant Channel as Email/SMS/Push Log
    Admin->>API: PUT /api/jadwal/{id}
    API->>Service: update(id, data)
    Service->>DB: Lock resources; check conflicts/capacity
    alt Invalid schedule
        Service-->>API: SchedulingError 409
    else Valid changed schedule
        Service->>DB: UPDATE jadwal (uncommitted)
        Service->>Inv: invalidate(old/new kelas_id)
        Inv->>DB: KRS transition SISTEM→revision; log+notification
        Service->>DB: INSERT schedule_outbox(pending)
        Service->>DB: COMMIT (atomic)
        Service->>Disp: run() after commit
        Disp->>DB: SELECT pending outbox
        Disp->>Subject: notify(event)
        loop Each observer (isolated try/except)
            Subject->>Obs: update(event)
            Obs->>Channel: send(key=event+observer+recipient+channel)
            Channel->>DB: INSERT delivery receipt (dedup)
            Channel-->>Obs: Simulated log
        end
        Disp->>DB: COMMIT receipts + status sent/pending/failed
        Service-->>API: Jadwal updated
    end
    API-->>Admin: HTTP response
```

**Batasan:** SQLite tidak memiliki `SKIP LOCKED`; gunakan satu dispatcher worker. Simulasi kanal tidak mengirim pesan sungguhan. `LogChannel` mencatat receipt di database sebelum logging; untuk gateway sungguhan perlu dukungan idempotency provider. Pada implementasi demo, dispatcher dijalankan langsung setelah commit dan kegagalannya tidak membatalkan jadwal.
