"""Golden dataset seeder: 3 evaluation suites x 12 golden cases (36 total) + 9 pre-evaluated runs."""

from __future__ import annotations

from backend.evaluator import evaluate_case_with_pipeline, summarize_run_metrics
from backend.models import (
    CorpusPassage,
    EvalCaseCreate,
    EvalRun,
    ExecuteRunRequest,
    ExpectedToolCall,
    FieldConstraint,
    GatePolicy,
    SchemaContract,
)
from backend.store import VerdictStore


def _citation_schema() -> SchemaContract:
    return SchemaContract(
        name="GroundedCitationResponse",
        required_fields=["answer", "citations", "confidence"],
        fields={
            "answer": FieldConstraint(type="string", required=True, min_length=20),
            "citations": FieldConstraint(type="array", required=True, min_length=1),
            "confidence": FieldConstraint(type="number", required=True, min_value=0.0, max_value=1.0),
        },
    )


def _rag_grounding_cases() -> list[EvalCaseCreate]:
    schema = _citation_schema()
    return [
        EvalCaseCreate(
            case_code="RG-01",
            title="Audit Log Retention & WORM Storage Compliance",
            category="compliance",
            query="How long are immutable enterprise audit logs kept in hot storage versus cold archival?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-RG-101",
                    title="Security Audit Log Retention Standard",
                    text="Enterprise security audit logs remain searchable in hot NVMe storage for 365 days. After 365 days, logs roll into Glacier WORM cold archival for 7 years with S3 Object Lock enabled.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-102",
                    title="Compliance Archival Export Guide",
                    text="Audit export bundles include SHA-256 manifests signed by KMS and cannot be deleted early while Object Lock compliance mode is active.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-103",
                    title="Application Debug Trace Sampling",
                    text="Non-security application debug traces use 90-day retention in ephemeral storage and do not enter immutable WORM vaults.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-104",
                    title="Developer Sandbox Reset Policy",
                    text="Sandbox environments automatically purge transient logs every 14 days when workspaces are idle.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-105",
                    title="Workspace UI Telemetry Retention",
                    text="Frontend clickstream telemetry is aggregated hourly and discarded after 30 days.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-RG-101": 2.0, "DOC-RG-102": 1.0},
            expected_claims=[
                "Enterprise security audit logs stay in hot storage for 365 days.",
                "Logs move to Glacier WORM archival for 7 years with S3 Object Lock.",
            ],
            forbidden_claims=[
                "Audit logs are deleted automatically after 90 days in cold storage.",
            ],
            schema_contract=schema,
        ),
        EvalCaseCreate(
            case_code="RG-02",
            title="Enterprise SLA Uptime & Incident Credit Schedule",
            category="sla",
            query="What monthly uptime guarantee applies to Enterprise accounts and what credit tiers apply on breach?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-RG-201",
                    title="Enterprise Service Level Agreement v4",
                    text="Enterprise plans carry a 99.95% monthly uptime commitment. If monthly availability drops below 99.95% but stays at or above 99.0%, customers receive a 10% invoice credit; drops below 99.0% trigger a 25% invoice credit.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-202",
                    title="SLA Credit Claim Window",
                    text="Service credit requests must be submitted within 30 calendar days after the incident month closes.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-203",
                    title="Internal SRE Error Budget Goal",
                    text="Internal SRE teams target an aspirational 99.99% reliability objective for alert thresholds, which is non-contractual.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-204",
                    title="Scheduled Maintenance Notice Rules",
                    text="Planned maintenance windows announced 72 hours ahead are excluded from SLA downtime calculations.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-205",
                    title="Free Tier Availability Disclaimer",
                    text="Free tier workspaces are provided on a best-effort basis without financial SLA credits.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-RG-201": 2.0, "DOC-RG-202": 1.0},
            expected_claims=[
                "Enterprise plans guarantee 99.95% monthly uptime.",
                "Breaches below 99.95% qualify for a 10% credit and below 99.0% qualify for a 25% credit.",
            ],
            forbidden_claims=[
                "Customers receive an automatic 50% credit whenever internal 99.99% targets miss.",
            ],
            schema_contract=schema,
        ),
        EvalCaseCreate(
            case_code="RG-03",
            title="KMS Customer-Managed Key Rotation & Cipher",
            category="security",
            query="Which symmetric cipher and automatic rotation cadence govern customer-managed KMS keys?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-RG-301",
                    title="Envelope Encryption Architecture",
                    text="Tenant data at rest uses AES-256-GCM envelope encryption. Customer-managed KMS root keys rotate automatically every 90 days without downtime.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-302",
                    title="Key Version Retention During Rotation",
                    text="Previous KMS key versions stay active for decryption until background re-encryption completes within 48 hours.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-303",
                    title="TLS Ingress Session Ticket Policy",
                    text="Edge load balancers rotate TLS 1.3 session ticket encryption keys every 24 hours.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-304",
                    title="SSH Bastion Certificate TTL",
                    text="Engineers obtain ephemeral SSH certificates valid for 8 hours via hardware MFA.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-305",
                    title="Password Hashing Configuration",
                    text="Interactive user passwords use Argon2id with 64 MiB memory cost.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-RG-301": 2.0, "DOC-RG-302": 1.0},
            expected_claims=[
                "Data at rest is encrypted with AES-256-GCM.",
                "Customer-managed KMS keys rotate automatically every 90 days.",
            ],
            forbidden_claims=[
                "KMS root keys rotate every 24 hours using RSA-1024.",
            ],
            schema_contract=schema,
        ),
        EvalCaseCreate(
            case_code="RG-04",
            title="Severity-1 Incident Pager Escalation Timing",
            category="operations",
            query="What are the acknowledgement and executive escalation windows for a Severity-1 production incident?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-RG-401",
                    title="Production Incident Runbook Matrix",
                    text="Severity-1 outages require primary on-call acknowledgement within 15 minutes. If unmitigated or unacknowledged after 30 minutes, the incident commander and VP of Engineering are automatically paged.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-402",
                    title="Customer Status Page Update Cadence",
                    text="During active Severity-1 incidents, status page updates must be published every 30 minutes until resolution.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-403",
                    title="Severity-3 Ticket Triage SLA",
                    text="Low-impact Severity-3 support tickets are triaged within 48 business hours.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-404",
                    title="Postmortem Blameless Review Schedule",
                    text="Written postmortem reviews must be completed within 5 business days of incident closure.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-405",
                    title="Staging Cluster Alert Routing",
                    text="Staging environment alerts post only to Slack without paging on-call engineers.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-RG-401": 2.0, "DOC-RG-402": 1.0},
            expected_claims=[
                "Severity-1 incidents require on-call acknowledgement within 15 minutes.",
                "Executive escalation pages automatically at 30 minutes.",
            ],
            forbidden_claims=[
                "Severity-1 outages allow 48 hours before engineering escalation.",
            ],
            schema_contract=schema,
        ),
        EvalCaseCreate(
            case_code="RG-05",
            title="GDPR Subject Erasure & Backup Tombstone Expiry",
            category="compliance",
            query="Within how many days are GDPR erasure requests purged from primary stores and backup snapshots?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-RG-501",
                    title="GDPR Right-to-Erasure Runbook",
                    text="Verified GDPR deletion requests purge primary customer PII records within 30 calendar days. Encrypted incremental backup tombstones expire completely within 14 additional days.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-502",
                    title="Erasure Confirmation Certificate",
                    text="The privacy controller emits a signed deletion receipt once primary and search index purges finish.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-503",
                    title="Warehouse Analytics Anonymization Job",
                    text="Aggregated product analytics pipelines strip user identifiers within 7 days of ingestion.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-504",
                    title="Invoice Tax Record Statutory Hold",
                    text="Statutory tax invoices remain retained for 6 years as mandated by fiscal regulations.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-505",
                    title="Cookie Consent Banner Renewal",
                    text="Browser consent preferences are re-prompted every 12 months.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-RG-501": 2.0, "DOC-RG-502": 1.0},
            expected_claims=[
                "Primary PII records are purged within 30 calendar days.",
                "Encrypted backup tombstones expire within 14 additional days.",
            ],
            forbidden_claims=[
                "Backup snapshots retain unencrypted PII for 6 years after erasure.",
            ],
            schema_contract=schema,
        ),
        EvalCaseCreate(
            case_code="RG-06",
            title="Public API Rate Limiting & Retry-After Contract",
            category="api",
            query="What is the standard tier API request quota and how should clients handle HTTP 429 responses?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-RG-601",
                    title="Gateway Throttling & Rate Limit Spec",
                    text="Standard API workspaces are limited to 1200 requests per minute per organization key. Exceeding the bucket returns HTTP 429 with a Retry-After header; clients must use exponential backoff with jitter.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-602",
                    title="Burst Token Bucket Smoothing",
                    text="Up to 100 burst requests above steady rate are absorbed over a 5-second sliding window.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-603",
                    title="Outbound Webhook Delivery Rate",
                    text="Platform webhook dispatchers cap outbound notifications at 50 requests per second per customer receiver.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-604",
                    title="GraphQL Query Depth Limit",
                    text="GraphQL endpoints reject nested queries exceeding a depth of 8 levels with HTTP 400.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-605",
                    title="Batch Upload File Size Limit",
                    text="Multipart document ingestion accepts payloads up to 250 MB per request.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-RG-601": 2.0, "DOC-RG-602": 1.0},
            expected_claims=[
                "Standard API workspaces allow 1200 requests per minute.",
                "HTTP 429 responses include a Retry-After header and require exponential backoff with jitter.",
            ],
            forbidden_claims=[
                "Standard API clients receive 50000 requests per minute without throttling.",
            ],
            schema_contract=schema,
        ),
        EvalCaseCreate(
            case_code="RG-07",
            title="Zero-Downtime Blue/Green Database Cutover",
            category="database",
            query="How long do dual-write verification and the final read-only lock last during blue/green database cutover?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-RG-701",
                    title="Blue/Green Postgres Cutover SOP",
                    text="Before cutover, logical replication runs dual-write checksum verification for 20 minutes. During final DNS and pooler switchover, a brief read-only lock lasts at most 15 seconds.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-702",
                    title="Replication Lag Gate Check",
                    text="Cutover automation aborts automatically if replica lag exceeds 100 milliseconds at switchover time.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-703",
                    title="Local Staging Seed Script",
                    text="Developer staging databases reload synthetic fixtures in 4 minutes via pg_restore.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-704",
                    title="Schema Migration Lock Timeout",
                    text="Routine DDL migrations enforce a 2-second lock_timeout to protect live query latency.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-705",
                    title="Nightly Vacuum Maintenance Window",
                    text="Autovacuum analyze thresholds trigger when 5% of table tuples change.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-RG-701": 2.0, "DOC-RG-702": 1.0},
            expected_claims=[
                "Dual-write checksum verification runs for 20 minutes.",
                "The final read-only lock lasts at most 15 seconds.",
            ],
            forbidden_claims=[
                "Blue/green cutover requires a 4-hour full offline maintenance lock.",
            ],
            schema_contract=schema,
        ),
        EvalCaseCreate(
            case_code="RG-08",
            title="Enterprise Overage Multiplier & Grace Period",
            category="billing",
            query="What grace period and overage rate apply when an Enterprise workspace exceeds annual token commit?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-RG-801",
                    title="Enterprise Usage & Overage Terms",
                    text="Enterprise accounts receive a 15-day grace window after crossing 100% of annual committed capacity. Continued overages bill monthly at a 1.5x metered unit multiplier.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-802",
                    title="Automated Spend Alert Thresholds",
                    text="Billing admins receive webhook and email alerts at 80% and 100% utilization.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-803",
                    title="Trial Workspace Expiration Rule",
                    text="Self-serve trial workspaces pause execution automatically after a 7-day grace period.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-804",
                    title="Wire Transfer Payment Net Terms",
                    text="Annual enterprise invoices carry Net-30 payment terms via ACH or wire.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-805",
                    title="Seat License Proration Formula",
                    text="Added developer seats are prorated daily across the remaining billing cycle.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-RG-801": 2.0, "DOC-RG-802": 1.0},
            expected_claims=[
                "Enterprise accounts get a 15-day grace window after exceeding annual commit.",
                "Overages are billed at a 1.5x metered multiplier.",
            ],
            forbidden_claims=[
                "Enterprise workspaces are immediately suspended after 7 days with a 3x penalty.",
            ],
            schema_contract=schema,
        ),
        EvalCaseCreate(
            case_code="RG-09",
            title="RBAC Service Account OIDC Token Lifetime",
            category="security",
            query="What is the maximum lifetime for workload OIDC tokens and how many active signing keys are allowed?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-RG-901",
                    title="Workload Identity Federation Policy",
                    text="Service accounts authenticate with short-lived 60-minute OIDC bearer tokens signed by asymmetric keys. Organizations may maintain at most 3 active signing keys simultaneously.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-902",
                    title="Token Audience Validation Rule",
                    text="Gateways strictly reject OIDC tokens missing the scoped tenant audience claim.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-903",
                    title="Interactive Browser SSO Cookie TTL",
                    text="Human console sessions use HTTP-only SAML cookies expiring after 12 hours of inactivity.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-904",
                    title="API Key Prefix Format",
                    text="Legacy static developer keys use a 32-character base62 token body.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-905",
                    title="IP Allowlist CIDR Limit",
                    text="Each organization may configure up to 50 CIDR blocks in network ingress rules.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-RG-901": 2.0, "DOC-RG-902": 1.0},
            expected_claims=[
                "Workload OIDC tokens expire after 60 minutes.",
                "Organizations may have at most 3 active signing keys.",
            ],
            forbidden_claims=[
                "Service account tokens remain valid for 12 hours and allow 10 signing keys.",
            ],
            schema_contract=schema,
        ),
        EvalCaseCreate(
            case_code="RG-10",
            title="Multi-Region Disaster Recovery RPO & RTO",
            category="reliability",
            query="What Recovery Point Objective (RPO) and Recovery Time Objective (RTO) govern regional failover?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-RG-1001",
                    title="Cross-Region DR Architecture Specification",
                    text="Active-passive cross-region failover guarantees an RPO of <= 5 minutes using asynchronous WAL streaming and an RTO of <= 20 minutes via automated DNS promotion.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-1002",
                    title="Quarterly Failover GameDay Validation",
                    text="Chaos failover drills execute quarterly against secondary regions to verify RTO compliance.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-1003",
                    title="Cold Archival Bucket Sync Cadence",
                    text="Cold analytics Parquet exports synchronize across regions once every 24 hours.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-1004",
                    title="CDN Edge Cache TTL Defaults",
                    text="Static dashboard assets cache at edge POPs for 300 seconds.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-1005",
                    title="Local Availability Zone Health Probe",
                    text="Internal load balancers probe worker health endpoints every 5 seconds.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-RG-1001": 2.0, "DOC-RG-1002": 1.0},
            expected_claims=[
                "Regional failover guarantees RPO <= 5 minutes via asynchronous WAL streaming.",
                "Automated promotion delivers RTO <= 20 minutes.",
            ],
            forbidden_claims=[
                "Cross-region disaster recovery has a 24-hour RPO window.",
            ],
            schema_contract=schema,
        ),
        EvalCaseCreate(
            case_code="RG-11",
            title="Critical CVE Remediation & Patching SLAs",
            category="security",
            query="What patching deadlines apply to Critical (CVSS >= 9.0) versus High (CVSS 7.0-8.9) vulnerabilities?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-RG-1101",
                    title="Vulnerability Management SLA Policy",
                    text="Critical CVEs with CVSS >= 9.0 must be remediated and deployed within 24 hours of disclosure. High-severity CVEs scoring 7.0 to 8.9 must be patched within 7 calendar days.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-1102",
                    title="Container Image SBOM Attestation",
                    text="CI pipelines fail automatically if base images carry unpatched Critical vulnerabilities.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-1103",
                    title="Open-Source License Compliance Review",
                    text="Dependency license compatibility audits run on a monthly cadence.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-1104",
                    title="Bug Bounty Payout Tiers",
                    text="External researcher disclosures qualify for triage rewards within 72 hours.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-1105",
                    title="Annual Penetration Test Schedule",
                    text="Third-party grey-box penetration testing occurs once every 12 months.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-RG-1101": 2.0, "DOC-RG-1102": 1.0},
            expected_claims=[
                "Critical CVEs (CVSS >= 9.0) must be patched within 24 hours.",
                "High CVEs (CVSS 7.0-8.9) must be patched within 7 calendar days.",
            ],
            forbidden_claims=[
                "Critical CVEs are deferred to the monthly license audit cycle.",
            ],
            schema_contract=schema,
        ),
        EvalCaseCreate(
            case_code="RG-12",
            title="Multi-Tenant Vector Namespace Isolation & Erasure",
            category="architecture",
            query="How are tenant vector namespaces isolated at rest and how quickly does cryptographic erasure complete?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-RG-1201",
                    title="Tenant Vector Partitioning Specification",
                    text="Each tenant vector namespace uses a dedicated per-tenant KMS data key and shard partition. Deleting a namespace revokes its tenant key immediately and completes cryptographic erasure within 2 hours.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-1202",
                    title="HNSW Index Compaction Behavior",
                    text="Deleted vector tombstones are reclaimed during nightly HNSW segment compaction.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-1203",
                    title="Shared Evaluation Sandbox Purge",
                    text="Shared developer test collections expire every 48 hours without tenant KMS isolation.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-1204",
                    title="Embedding Dimension Normalization",
                    text="Dense vectors are L2-normalized to 1536 dimensions before indexing.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-RG-1205",
                    title="Metadata Filter Cardinality Limit",
                    text="Queries support up to 16 boolean metadata predicates per search call.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-RG-1201": 2.0, "DOC-RG-1202": 1.0},
            expected_claims=[
                "Each tenant namespace uses a dedicated KMS data key and shard partition.",
                "Cryptographic erasure completes within 2 hours of key revocation.",
            ],
            forbidden_claims=[
                "All tenants share a single unencrypted index purged only every 48 hours.",
            ],
            schema_contract=schema,
        ),
    ]


def _hybrid_retrieval_cases() -> list[EvalCaseCreate]:
    schema = _citation_schema()
    return [
        EvalCaseCreate(
            case_code="HR-01",
            title="Tail Latency Mitigation During Hot Partition Spikes",
            category="distributed-systems",
            query="How do we reduce tail latency when hot partition spikes overload a single shard?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-HR-101",
                    title="p99 Mitigation Under Key Skew",
                    text="Mitigating p99 degradation under severe key skew requires consistent hashing with bounded-load virtual nodes and salted composite keys to spread hotspot traffic across replicas.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-102",
                    title="Adaptive Request Hedging for Slow Replicas",
                    text="Sending hedged read requests after the 95th percentile delay threshold suppresses tail jitter during transient shard saturation.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-103",
                    title="UI Chart Tooltip Animation Latency",
                    text="When spikes appear on frontend latency charts, debounce tooltip hover events so frame latency stays below 16 milliseconds.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-104",
                    title="Hot Reload Dev Server Configuration",
                    text="Local Vite dev server hot module replacement spikes CPU briefly during initial partition compilation.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-105",
                    title="Batch Warehouse Partition Pruning",
                    text="Nightly Spark jobs partition historical tables by calendar date to speed up cold analytical scans.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-HR-101": 2.0, "DOC-HR-102": 1.0},
            expected_claims=[
                "Consistent hashing with bounded-load virtual nodes and salted keys mitigates p99 key skew.",
                "Hedged reads after the 95th percentile delay reduce tail jitter.",
            ],
            forbidden_claims=["Debouncing UI tooltip hover events fixes database shard hotspots."],
            schema_contract=schema,
        ),
        EvalCaseCreate(
            case_code="HR-02",
            title="Preventing Credential Leakage in CI Build Logs",
            category="security",
            query="How should build pipelines prevent secret leakage in continuous integration console output?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-HR-201",
                    title="Token Scrubbing & OIDC Ephemeral Credentials",
                    text="Replace static environment tokens with short-lived OIDC workload credentials and register regex maskers so CI runners redact bearer strings before streaming stdout.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-202",
                    title="Pre-Commit Secret Entropy Scanning",
                    text="Run automated entropy scanners on pull requests to block accidental key commits prior to pipeline execution.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-203",
                    title="CI Build Cache Compression Settings",
                    text="Compressing build dependency archives cuts CI pipeline duration and verbose output download time.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-204",
                    title="Continuous Integration Runner Disk Cleanup",
                    text="Ephemeral runners purge build directories and log files after job completion to free disk space.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-205",
                    title="Console Color Formatting Flags",
                    text="Disable ANSI escape sequences in CI output when archiving plain-text artifacts.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-HR-201": 2.0, "DOC-HR-202": 1.0},
            expected_claims=[
                "Use short-lived OIDC workload credentials and regex log maskers.",
                "Pre-commit entropy scanners block accidental secret commits.",
            ],
            forbidden_claims=["Compressing CI cache archives prevents token exposure in stdout."],
            schema_contract=schema,
        ),
        EvalCaseCreate(
            case_code="HR-03",
            title="Idempotent Handling of Duplicate Webhook Deliveries",
            category="api-reliability",
            query="What mechanism ensures duplicate webhook retries do not double-charge or mutate state twice?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-HR-301",
                    title="At-Least-Once Event Deduplication Pattern",
                    text="Receivers must record each event delivery UUID in an atomic unique-constraint ledger table and verify the HMAC-SHA256 signature so repeated webhook retries become safe no-ops.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-302",
                    title="Idempotency Window TTL",
                    text="Processed event keys remain indexed for 72 hours to cover full exponential retry schedules.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-303",
                    title="Webhook Payload JSON Pretty Printing",
                    text="Outgoing webhook payloads omit whitespace formatting to shrink network payload bytes.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-304",
                    title="Duplicate CSV Upload Warning",
                    text="The admin portal warns users if they attempt to upload duplicate webhook test fixtures.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-305",
                    title="HTTP Keep-Alive Pool Tuning",
                    text="Reusing outbound TCP sockets cuts TLS handshake overhead during webhook bursts.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-HR-301": 2.0, "DOC-HR-302": 1.0},
            expected_claims=[
                "Store each event UUID in a unique-constraint table and verify HMAC-SHA256 signatures.",
                "Retain processed event keys for 72 hours across retry windows.",
            ],
            forbidden_claims=["Disabling webhook retries guarantees exactly-once TCP delivery."],
            schema_contract=schema,
        ),
        EvalCaseCreate(
            case_code="HR-04",
            title="Serverless PostgreSQL Connection Pooling Under Bursts",
            category="database",
            query="How do ephemeral serverless functions avoid exhausting PostgreSQL max_connections during traffic bursts?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-HR-401",
                    title="Transaction-Mode PgBouncer Multiplexing",
                    text="Route ephemeral lambda workers through transaction-mode PgBouncer or an HTTP SQL proxy so thousands of concurrent invocations multiplex onto a bounded backend pool of 50 Postgres slots.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-402",
                    title="Prepared Statement Compatibility in Transaction Pooling",
                    text="Disable server-side session prepared statements or enable protocol-level statement tracking when using transaction pooling.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-403",
                    title="Serverless Cold Start Bundle Minification",
                    text="Tree-shaking unused serverless dependencies cuts cold-start burst initialization by 180 milliseconds.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-404",
                    title="PostgreSQL Collation Locale Selection",
                    text="Default database clusters initialize with C.UTF-8 collation for deterministic sorting.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-405",
                    title="Idle Browser Websocket Timeout",
                    text="Client browsers reconnect websockets automatically after network sleep events.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-HR-401": 2.0, "DOC-HR-402": 1.0},
            expected_claims=[
                "Transaction-mode PgBouncer multiplexes serverless bursts onto a bounded Postgres backend pool.",
                "Disable incompatible session-level prepared statements under transaction pooling.",
            ],
            forbidden_claims=["Increasing PostgreSQL max_connections to 50000 eliminates pool overhead."],
            schema_contract=schema,
        ),
        EvalCaseCreate(
            case_code="HR-05",
            title="HNSW Vector Index Recall Degradation After Deletes",
            category="vector-search",
            query="Why does vector search recall degrade after heavy document deletions and how is it restored?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-HR-501",
                    title="Graph Connectivity & Tombstone Compaction",
                    text="Soft-deleted embeddings remain as tombstones inside HNSW navigation layers, severing greedy routing paths and lowering top-K recall until segment compaction rebuilds neighborhood links.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-502",
                    title="Dynamic ef_search Oversampling",
                    text="Increasing runtime ef_search and oversampling candidate pools restores recall temporarily prior to scheduled compaction.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-503",
                    title="Vector Embedding Model Upgrade Checklist",
                    text="Changing embedding dimensions requires re-vectorizing historical text chunks before search cutover.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-504",
                    title="Full-Text Stemmer Stopword List",
                    text="BM25 lexical tokenizers strip common articles to compress inverted search indexes.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-505",
                    title="Object Storage Lifecycle Expiration",
                    text="Delete markers in archival storage wait 24 hours before physical block reclamation.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-HR-501": 2.0, "DOC-HR-502": 1.0},
            expected_claims=[
                "Soft-delete tombstones sever HNSW graph paths until segment compaction rebuilds links.",
                "Raising ef_search oversampling temporarily recovers top-K recall.",
            ],
            forbidden_claims=["HNSW tombstones automatically improve cosine recall without compaction."],
            schema_contract=schema,
        ),
        EvalCaseCreate(
            case_code="HR-06",
            title="Graceful Degradation When Downstream Gateway Stalls",
            category="resilience",
            query="What resilience pattern prevents thread starvation when an external payment gateway hangs?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-HR-601",
                    title="Circuit Breakers & Bulkhead Isolation",
                    text="Enforce strict 2-second socket timeouts, wrap downstream calls in a half-open circuit breaker, and isolate worker threads inside bounded bulkheads so upstream stalls fail fast.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-602",
                    title="Queued Deferred Reconciliation Fallback",
                    text="When the breaker opens, queue non-urgent reconciliation tasks in a dead-letter retry topic for asynchronous recovery.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-603",
                    title="Payment Receipt PDF Font Embedding",
                    text="Customer invoice PDFs embed subsetted fonts for offline archive readability.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-604",
                    title="Gateway Webhook IP Rotation Calendar",
                    text="External payment providers publish static egress CIDR updates quarterly.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-605",
                    title="UI Loading Spinner Threshold",
                    text="Frontend components show a skeleton loader if payment confirmation takes over 300ms.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-HR-601": 2.0, "DOC-HR-602": 1.0},
            expected_claims=[
                "Strict timeouts, circuit breakers, and bounded bulkheads prevent upstream thread exhaustion.",
                "Deferred tasks route to a retry topic while the breaker is open.",
            ],
            forbidden_claims=["Removing HTTP timeouts allows stalled payment threads to finish cleanly."],
            schema_contract=schema,
        ),
        EvalCaseCreate(
            case_code="HR-07",
            title="Diagnosing OOMKills in Kubernetes Worker Pods",
            category="infrastructure",
            query="How do operators diagnose and prevent sudden out-of-memory container kills in worker pods?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-HR-701",
                    title="Cgroup Memory Working-Set & Heap Profiling",
                    text="Exit code 137 indicates cgroup OOMKills; inspect container_memory_working_set_bytes alongside jemalloc heap profiles and cap concurrent batch prefetch buffers below 75% of pod limits.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-702",
                    title="Memory Request Equals Limit Best Practice",
                    text="Setting Kubernetes memory requests equal to limits secures Guaranteed QoS class against node eviction.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-703",
                    title="Kubernetes Pod Readiness Probe Delay",
                    text="Adjust initialDelaySeconds on worker readiness probes so slow startup models pass health checks.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-704",
                    title="Worker Pod Horizontal Autoscaler CPU Target",
                    text="HPA scales worker replicas when sustained CPU utilization exceeds 70%.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-705",
                    title="Container Registry Image Layer Caching",
                    text="Multi-stage Docker builds reduce worker image pull time across cluster nodes.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-HR-701": 2.0, "DOC-HR-702": 1.0},
            expected_claims=[
                "Exit code 137 reflects cgroup OOMKills; inspect working-set memory and heap profiles.",
                "Set memory requests equal to limits for Guaranteed QoS protection.",
            ],
            forbidden_claims=["Exit code 137 indicates graceful Kubernetes pod shutdown."],
            schema_contract=schema,
        ),
        EvalCaseCreate(
            case_code="HR-08",
            title="Migrating Legacy Auth Flows to OAuth2 PKCE",
            category="security",
            query="Why should native and browser apps replace implicit grant auth with Authorization Code + PKCE?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-HR-801",
                    title="OAuth 2.1 Authorization Code with PKCE",
                    text="PKCE binds the authorization code to a cryptographic SHA-256 code_verifier, preventing code interception attacks and eliminating exposed access tokens in browser URL fragments.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-802",
                    title="Refresh Token Rotation on Public Clients",
                    text="Rotate single-use refresh tokens on every exchange and revoke the token family on reuse detection.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-803",
                    title="CORS Preflight Cache Duration",
                    text="Configure Access-Control-Max-Age to 600 seconds to trim redundant OPTIONS requests.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-804",
                    title="Legacy App Icon Asset Migration",
                    text="Replace raster PNG app icons with crisp SVG assets across mobile login screens.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-805",
                    title="Session Timeout Banner Copy",
                    text="Display a countdown toast 2 minutes prior to interactive session expiry.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-HR-801": 2.0, "DOC-HR-802": 1.0},
            expected_claims=[
                "PKCE binds authorization codes with a SHA-256 code_verifier and removes tokens from URL fragments.",
                "Single-use refresh token rotation mitigates stolen token replay.",
            ],
            forbidden_claims=["Implicit grant embeds safer tokens directly in browser URL fragments."],
            schema_contract=schema,
        ),
        EvalCaseCreate(
            case_code="HR-09",
            title="Zero-Copy Streaming for Large Parquet Exports",
            category="data-engineering",
            query="How can analytics APIs export multi-gigabyte Parquet files without buffering the whole dataset in RAM?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-HR-901",
                    title="Arrow RecordBatch Chunked Streaming",
                    text="Stream Apache Arrow RecordBatches in 64 MB row groups directly through an async multipart S3 uploader or HTTP chunked response, keeping worker RSS memory constant under 256 MB.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-902",
                    title="Dictionary Encoding for Parquet Columns",
                    text="Enable ZSTD compression and dictionary encoding per row group to reduce transfer bytes by 4x.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-903",
                    title="Dashboard CSV Export Row Limit",
                    text="Interactive UI table exports truncate synchronous browser downloads at 50000 rows.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-904",
                    title="Analytics Chart Color Palette Contrast",
                    text="Use accessible plum and forest hues for multi-series analytics visualizations.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-905",
                    title="Query Result Pagination Offset Notice",
                    text="Prefer keyset cursor pagination over deep SQL OFFSET clauses.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-HR-901": 2.0, "DOC-HR-902": 1.0},
            expected_claims=[
                "Stream Arrow RecordBatches in 64 MB row groups to bound worker RAM under 256 MB.",
                "ZSTD and dictionary encoding shrink Parquet payload sizes.",
            ],
            forbidden_claims=["Load the entire multi-gigabyte dataframe into Python lists before serializing."],
            schema_contract=schema,
        ),
        EvalCaseCreate(
            case_code="HR-10",
            title="Mitigating Split-Brain Quorum Loss Across Zones",
            category="distributed-systems",
            query="How do consensus clusters prevent dual-leader writes during a network partition between zones?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-HR-1001",
                    title="Raft Majority Quorum & Fencing Tokens",
                    text="Deploy an odd number of voters across 3 availability zones so only a strict majority partition commits entries, paired with monotonic fencing tokens to reject stale deposed leaders.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-1002",
                    title="Leader Lease Expiry Validation",
                    text="Leaders step down automatically if heartbeat acknowledgements fail within the bounded election lease.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-1003",
                    title="Zone DNS Round-Robin Balancing",
                    text="Configure weighted DNS records to distribute stateless HTTP traffic across zones.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-1004",
                    title="Network Bandwidth Billing Across Zones",
                    text="Cross-AZ data transfer incurs metered egress fees for uncached object reads.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-1005",
                    title="SSH Tunnel Jump Host Guide",
                    text="Administrators connect to isolated subnets via audited WireGuard tunnels.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-HR-1001": 2.0, "DOC-HR-1002": 1.0},
            expected_claims=[
                "An odd number of voters across 3 zones ensures only a strict majority commits writes.",
                "Monotonic fencing tokens block stale deposed leaders.",
            ],
            forbidden_claims=["Two-node active clusters maintain safe quorum without a tiebreaker witness."],
            schema_contract=schema,
        ),
        EvalCaseCreate(
            case_code="HR-11",
            title="Compressing Telemetry Payloads Without Losing Spans",
            category="observability",
            query="How can distributed tracing collectors cut ingest bandwidth without dropping error trace spans?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-HR-1101",
                    title="Tail-Based Error Sampling & Protobuf ZSTD",
                    text="Use OTLP gRPC batches compressed with ZSTD alongside tail-based sampling that retains 100% of error or high-latency traces while sampling healthy fast spans at 5%.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-1102",
                    title="Span Attribute Cardinality Guardrails",
                    text="Drop high-cardinality raw SQL literals from span attributes at the collector processor layer.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-1103",
                    title="Log Retention Bucket Lifecycle",
                    text="Archived collector logs transition to cold storage after 60 days.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-1104",
                    title="Browser Performance Navigation Timing",
                    text="Capture Web Vitals LCP and INP metrics via lightweight beacon payloads.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-1105",
                    title="Dashboard Dark Ink Contrast Standards",
                    text="Charts maintain 4.5:1 contrast across axis labels and error bars.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-HR-1101": 2.0, "DOC-HR-1102": 1.0},
            expected_claims=[
                "ZSTD-compressed OTLP batches paired with tail-based sampling retain 100% of error traces.",
                "Healthy fast spans are sampled at 5% while dropping high-cardinality literals.",
            ],
            forbidden_claims=["Head-based 1% random sampling preserves all rare error traces."],
            schema_contract=schema,
        ),
        EvalCaseCreate(
            case_code="HR-12",
            title="Per-Tenant GPU Inference Queue Fairness",
            category="ml-infra",
            query="How does the inference scheduler prevent one noisy tenant from starving other tenants' GPU latency?",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-HR-1201",
                    title="Weighted Fair Queuing & Continuous Batching",
                    text="The GPU router uses deficit round-robin fair queuing per tenant coupled with token-budget admission caps so continuous batching preserves interactive TTFT under heavy batch load.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-1202",
                    title="KV-Cache Prefix Isolation Policy",
                    text="Logical KV-cache blocks enforce strict tenant isolation and evict idle prefixes via LRU.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-1203",
                    title="GPU Driver Firmware Upgrade Notes",
                    text="Upgrade CUDA kernel drivers on staging nodes before draining production inference pools.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-1204",
                    title="Model Checkpoint Weights Checksum",
                    text="Verify safetensors SHA-256 digests when syncing model artifacts from object storage.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-HR-1205",
                    title="Prompt Playground Slider Defaults",
                    text="Default playground temperature is set to 0.2 with a 1024-token output cap.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-HR-1201": 2.0, "DOC-HR-1202": 1.0},
            expected_claims=[
                "Deficit round-robin fair queuing and token-budget admission caps protect interactive TTFT.",
                "KV-cache blocks enforce tenant isolation with LRU eviction.",
            ],
            forbidden_claims=["Single FIFO queues protect interactive latency during bulk tenant floods."],
            schema_contract=schema,
        ),
    ]


def _tool_schema_cases() -> list[EvalCaseCreate]:
    return [
        EvalCaseCreate(
            case_code="TS-01",
            title="Authorize Enterprise Order Refund",
            category="finops-agent",
            query="Customer requests a $240 refund on order ORD-8841 due to duplicate billing. Verify eligibility and issue refund.",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-TS-101",
                    title="Refund Authorization Tool Spec",
                    text="Always call verify_refund_eligibility(order_id) first. Refunds up to $500 for duplicate billing are approved; execute issue_refund(order_id, amount_usd) after verification.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-102",
                    title="Refund Schema Rules",
                    text="Final response must report decision='approved', order_id, amount_usd, and citations.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-103",
                    title="Chargeback Dispute Litigation Flow",
                    text="Card network chargebacks over $2500 require legal counsel sign-off.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-104",
                    title="Promo Coupon Expiry Rules",
                    text="Expired promotional coupons cannot be reissued as cash refunds.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-105",
                    title="Monthly Invoice PDF Archive",
                    text="Customers download historical receipts from the billing tab.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-TS-101": 2.0, "DOC-TS-102": 1.0},
            expected_claims=[
                "verify_refund_eligibility must run before issue_refund.",
                "Duplicate billing refunds up to $500 are approved for $240.",
            ],
            forbidden_claims=["Issue a $900 refund without calling verify_refund_eligibility."],
            expected_tools=[
                ExpectedToolCall(name="verify_refund_eligibility", required_args={"order_id": "ORD-8841"}),
                ExpectedToolCall(name="issue_refund", required_args={"order_id": "ORD-8841", "amount_usd": 240}),
            ],
            schema_contract=SchemaContract(
                name="RefundDecisionSchema",
                required_fields=["decision", "order_id", "amount_usd", "answer", "citations"],
                fields={
                    "decision": FieldConstraint(type="string", enum=["approved", "denied", "escalate"]),
                    "order_id": FieldConstraint(type="string", pattern=r"^ORD-\d+$"),
                    "amount_usd": FieldConstraint(type="number", min_value=0.0, max_value=500.0),
                    "answer": FieldConstraint(type="string", min_length=15),
                    "citations": FieldConstraint(type="array", min_length=1),
                },
            ),
        ),
        EvalCaseCreate(
            case_code="TS-02",
            title="Escalate Severity-1 Payment Incident",
            category="sre-agent",
            query="Checkout latency crossed 12s with 18% HTTP 502 errors on incident INC-4021. Lookup on-call and page primary SRE.",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-TS-201",
                    title="Pager Escalation Tool Contract",
                    text="For Severity-1 incident INC-4021, call lookup_oncall(service='checkout-api') before calling page_primary_sre(incident_id, severity='sev1').",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-202",
                    title="Incident Schema Guidelines",
                    text="Return incident_id, severity enum ('sev1','sev2','sev3'), escalated boolean, answer, and citations.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-203",
                    title="Staging Slack Notification Format",
                    text="Non-prod errors route only to #staging-alerts.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-204",
                    title="Postmortem Template Fields",
                    text="Include root cause timeline and action items in postmortems.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-205",
                    title="Load Test Synthetic Traffic Window",
                    text="Weekly synthetic load benchmarks run Sundays at 03:00 UTC.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-TS-201": 2.0, "DOC-TS-202": 1.0},
            expected_claims=[
                "Call lookup_oncall for checkout-api before paging primary SRE for INC-4021.",
            ],
            forbidden_claims=["Silence Severity-1 payment errors as a sev3 alert."],
            expected_tools=[
                ExpectedToolCall(name="lookup_oncall", required_args={"service": "checkout-api"}),
                ExpectedToolCall(name="page_primary_sre", required_args={"incident_id": "INC-4021", "severity": "sev1"}),
            ],
            schema_contract=SchemaContract(
                name="IncidentEscalationSchema",
                required_fields=["incident_id", "severity", "escalate", "answer", "citations"],
                fields={
                    "incident_id": FieldConstraint(type="string", pattern=r"^INC-\d+$"),
                    "severity": FieldConstraint(type="string", enum=["sev1", "sev2", "sev3"]),
                    "escalate": FieldConstraint(type="boolean"),
                    "answer": FieldConstraint(type="string", min_length=15),
                    "citations": FieldConstraint(type="array", min_length=1),
                },
            ),
        ),
        EvalCaseCreate(
            case_code="TS-03",
            title="Rotate Compromised IAM Service Key",
            category="security-agent",
            query="Service key KEY-772 was spotted in a public repo. Audit usage, revoke KEY-772, and issue a replacement key.",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-TS-301",
                    title="Compromised Credential Playbook",
                    text="Execute inspect_audit_trail(key_id='KEY-772'), then revoke_key(key_id='KEY-772'), and finally issue_replacement_key(key_id='KEY-772'). Revoking before inspecting audit context is permitted only after trail capture.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-302",
                    title="Key Rotation Output Contract",
                    text="Schema requires status='rotated', key_id, requires_approval boolean, answer, and citations.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-303",
                    title="Hardware MFA Enrollment SOP",
                    text="Human administrators register two FIDO2 security keys.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-304",
                    title="SAML Metadata XML Refresh",
                    text="Identity provider certificates update every 24 months.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-305",
                    title="Read-Only Auditor Role Permissions",
                    text="External auditors receive time-boxed read permissions.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-TS-301": 2.0, "DOC-TS-302": 1.0},
            expected_claims=[
                "Inspect the audit trail for KEY-772, revoke the key, and issue a replacement.",
            ],
            forbidden_claims=["Leave KEY-772 active for 30 days before revoking."],
            expected_tools=[
                ExpectedToolCall(name="inspect_audit_trail", required_args={"key_id": "KEY-772"}),
                ExpectedToolCall(name="revoke_key", required_args={"key_id": "KEY-772"}),
                ExpectedToolCall(name="issue_replacement_key", required_args={"key_id": "KEY-772"}),
            ],
            schema_contract=SchemaContract(
                name="KeyRotationSchema",
                required_fields=["status", "key_id", "requires_approval", "answer", "citations"],
                fields={
                    "status": FieldConstraint(type="string", enum=["rotated", "revoked_only", "blocked"]),
                    "key_id": FieldConstraint(type="string", pattern=r"^KEY-\d+$"),
                    "requires_approval": FieldConstraint(type="boolean"),
                    "answer": FieldConstraint(type="string", min_length=15),
                    "citations": FieldConstraint(type="array", min_length=1),
                },
            ),
        ),
        EvalCaseCreate(
            case_code="TS-04",
            title="Approve Tenant GPU Quota Bump",
            category="infra-agent",
            query="Tenant TEN-309 requested a GPU quota raise to 16 A100 nodes. Check billing standing and update quota.",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-TS-401",
                    title="GPU Quota Provisioning Policy",
                    text="Always invoke check_billing_standing(tenant_id='TEN-309') prior to update_quota(tenant_id='TEN-309', gpu_limit=16). Enterprise tenants in good standing qualify up to 32 GPUs.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-402",
                    title="Quota Update JSON Specification",
                    text="Return decision, tenant_id, gpu_limit integer between 1 and 32, answer, and citations.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-403",
                    title="Spot Instance Preemption Warning",
                    text="Preemptible worker nodes emit a 120-second shutdown notice.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-404",
                    title="Disk Snapshot Retention Policy",
                    text="EBS snapshots prune after 14 days in dev clusters.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-405",
                    title="CPU Burst Credit Documentation",
                    text="Burstable compute nodes accumulate credits during idle periods.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-TS-401": 2.0, "DOC-TS-402": 1.0},
            expected_claims=[
                "Check billing standing for TEN-309 before updating GPU quota to 16.",
            ],
            forbidden_claims=["Grant 128 GPUs immediately without verifying billing standing."],
            expected_tools=[
                ExpectedToolCall(name="check_billing_standing", required_args={"tenant_id": "TEN-309"}),
                ExpectedToolCall(name="update_quota", required_args={"tenant_id": "TEN-309", "gpu_limit": 16}),
            ],
            schema_contract=SchemaContract(
                name="QuotaUpdateSchema",
                required_fields=["decision", "tenant_id", "gpu_limit", "answer", "citations"],
                fields={
                    "decision": FieldConstraint(type="string", enum=["approved", "denied", "pending"]),
                    "tenant_id": FieldConstraint(type="string", pattern=r"^TEN-\d+$"),
                    "gpu_limit": FieldConstraint(type="integer", min_value=1, max_value=32),
                    "answer": FieldConstraint(type="string", min_length=15),
                    "citations": FieldConstraint(type="array", min_length=1),
                },
            ),
        ),
        EvalCaseCreate(
            case_code="TS-05",
            title="Trigger Canary Rollback on Error Spike",
            category="sre-agent",
            query="Canary deployment for service billing-worker shows error spikes. Fetch canary metrics and execute rollback.",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-TS-501",
                    title="Automated Canary Rollback Runbook",
                    text="Before rolling back, call fetch_canary_metrics(service='billing-worker') to confirm 5xx threshold breach, then invoke rollback_deployment(service='billing-worker', target='previous_stable').",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-502",
                    title="Canary Decision Contract",
                    text="Output action enum ('rollback','promote','hold'), service, rollback_required boolean, answer, and citations.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-503",
                    title="Helm Chart Linting Rules",
                    text="CI lints Kubernetes manifests before image promotion.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-504",
                    title="Blue-Green Ingress Weight Slider",
                    text="Canary shifts traffic from 5% to 25% over 15 minutes when healthy.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-505",
                    title="Container Base Image Tagging",
                    text="Pin immutable SHA digests in production deployment manifests.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-TS-501": 2.0, "DOC-TS-502": 1.0},
            expected_claims=[
                "Fetch canary metrics for billing-worker before rolling back to previous_stable.",
            ],
            forbidden_claims=["Promote the failing canary deployment to 100% traffic."],
            expected_tools=[
                ExpectedToolCall(name="fetch_canary_metrics", required_args={"service": "billing-worker"}),
                ExpectedToolCall(name="rollback_deployment", required_args={"service": "billing-worker", "target": "previous_stable"}),
            ],
            schema_contract=SchemaContract(
                name="CanaryActionSchema",
                required_fields=["action", "service", "rollback_required", "answer", "citations"],
                fields={
                    "action": FieldConstraint(type="string", enum=["rollback", "promote", "hold"]),
                    "service": FieldConstraint(type="string", min_length=3),
                    "rollback_required": FieldConstraint(type="boolean"),
                    "answer": FieldConstraint(type="string", min_length=15),
                    "citations": FieldConstraint(type="array", min_length=1),
                },
            ),
        ),
        EvalCaseCreate(
            case_code="TS-06",
            title="Export SOC2 Compliance Audit Bundle",
            category="compliance-agent",
            query="Admin requested a SOC2 audit log archive for organization ORG-512. Verify admin role and generate archive.",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-TS-601",
                    title="Compliance Archive Export Tool Policy",
                    text="Only verified organization admins may export SOC2 evidence. Call verify_admin_role(org_id='ORG-512') prior to generate_audit_archive(org_id='ORG-512', standard='soc2').",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-602",
                    title="Archive Export Schema Contract",
                    text="Emit status enum ('generated','denied'), org_id, verified boolean, answer, and citations.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-603",
                    title="Annual SOC2 Auditor NDA Procedure",
                    text="External firms sign mutual NDAs before vault links issue.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-604",
                    title="CSV Telemetry Column Headers",
                    text="Export CSV headers use lowercase snake_case column names.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-605",
                    title="Workspace Timezone Preferences",
                    text="UI timestamps default to UTC unless overridden per profile.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-TS-601": 2.0, "DOC-TS-602": 1.0},
            expected_claims=[
                "Verify admin role for ORG-512 before generating the SOC2 audit archive.",
            ],
            forbidden_claims=["Bypass admin role checks and email raw PII publicly."],
            expected_tools=[
                ExpectedToolCall(name="verify_admin_role", required_args={"org_id": "ORG-512"}),
                ExpectedToolCall(name="generate_audit_archive", required_args={"org_id": "ORG-512", "standard": "soc2"}),
            ],
            schema_contract=SchemaContract(
                name="AuditExportSchema",
                required_fields=["status", "org_id", "verified", "answer", "citations"],
                fields={
                    "status": FieldConstraint(type="string", enum=["generated", "denied"]),
                    "org_id": FieldConstraint(type="string", pattern=r"^ORG-\d+$"),
                    "verified": FieldConstraint(type="boolean"),
                    "answer": FieldConstraint(type="string", min_length=15),
                    "citations": FieldConstraint(type="array", min_length=1),
                },
            ),
        ),
        EvalCaseCreate(
            case_code="TS-07",
            title="Apply SLA Downtime Invoice Credit",
            category="finops-agent",
            query="Calculate downtime credit for invoice INV-9104 following verified SLA breach and post ledger credit.",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-TS-701",
                    title="SLA Ledger Credit Automation Spec",
                    text="Compute eligible credit first via compute_downtime_credit(invoice_id='INV-9104'), then apply credit with post_ledger_credit(invoice_id='INV-9104').",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-702",
                    title="Ledger Credit Schema Spec",
                    text="Return status enum ('posted','rejected'), invoice_id, approved boolean, answer, and citations.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-703",
                    title="Annual Contract Renewal Reminder",
                    text="Account managers send renewal quotes 60 days before term expiry.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-704",
                    title="Tax Exemption Certificate Upload",
                    text="Non-profit organizations attach W-9 forms in billing settings.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-705",
                    title="Currency Conversion Rounding Rule",
                    text="Multi-currency invoices round half-even to two decimal places.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-TS-701": 2.0, "DOC-TS-702": 1.0},
            expected_claims=[
                "Compute downtime credit for INV-9104 before posting the ledger credit.",
            ],
            forbidden_claims=["Post an arbitrary $5000 ledger credit without computing downtime."],
            expected_tools=[
                ExpectedToolCall(name="compute_downtime_credit", required_args={"invoice_id": "INV-9104"}),
                ExpectedToolCall(name="post_ledger_credit", required_args={"invoice_id": "INV-9104"}),
            ],
            schema_contract=SchemaContract(
                name="LedgerCreditSchema",
                required_fields=["status", "invoice_id", "approved", "answer", "citations"],
                fields={
                    "status": FieldConstraint(type="string", enum=["posted", "rejected"]),
                    "invoice_id": FieldConstraint(type="string", pattern=r"^INV-\d+$"),
                    "approved": FieldConstraint(type="boolean"),
                    "answer": FieldConstraint(type="string", min_length=15),
                    "citations": FieldConstraint(type="array", min_length=1),
                },
            ),
        ),
        EvalCaseCreate(
            case_code="TS-08",
            title="Quarantine Failing Webhook Endpoint",
            category="api-agent",
            query="Webhook WH-118 has returned 500 errors for 6 hours. Inspect delivery failures and disable the webhook.",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-TS-801",
                    title="Webhook Circuit Breaker Playbook",
                    text="Inspect failure history using check_delivery_failures(webhook_id='WH-118') and then quarantine via disable_webhook(webhook_id='WH-118', reason='consecutive_5xx').",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-802",
                    title="Webhook Action Output Contract",
                    text="Return action enum ('disabled','retained'), webhook_id, verified boolean, answer, and citations.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-803",
                    title="Webhook HMAC Header Verification",
                    text="Clients validate X-Verdict-Signature using SHA-256.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-804",
                    title="Webhook Retry Backoff Schedule",
                    text="Retries wait 1m, 5m, 15m, and 60m before dead-lettering.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-805",
                    title="Custom Event Payload Filters",
                    text="Subscribers filter events by suite_id or status.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-TS-801": 2.0, "DOC-TS-802": 1.0},
            expected_claims=[
                "Check delivery failures for WH-118 and disable the webhook for consecutive_5xx.",
            ],
            forbidden_claims=["Delete all customer event logs permanently when WH-118 returns 500."],
            expected_tools=[
                ExpectedToolCall(name="check_delivery_failures", required_args={"webhook_id": "WH-118"}),
                ExpectedToolCall(name="disable_webhook", required_args={"webhook_id": "WH-118", "reason": "consecutive_5xx"}),
            ],
            schema_contract=SchemaContract(
                name="WebhookQuarantineSchema",
                required_fields=["action", "webhook_id", "verified", "answer", "citations"],
                fields={
                    "action": FieldConstraint(type="string", enum=["disabled", "retained"]),
                    "webhook_id": FieldConstraint(type="string", pattern=r"^WH-\d+$"),
                    "verified": FieldConstraint(type="boolean"),
                    "answer": FieldConstraint(type="string", min_length=15),
                    "citations": FieldConstraint(type="array", min_length=1),
                },
            ),
        ),
        EvalCaseCreate(
            case_code="TS-09",
            title="Promote Read-Replica Failover Target",
            category="database-agent",
            query="Primary DB in us-west is unreachable; inspect replication lag on cluster DB-WEST-2 and promote replica.",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-TS-901",
                    title="Database Replica Promotion Procedure",
                    text="Always check replica currency with inspect_replication_lag(cluster_id='DB-WEST-2') before calling promote_replica(cluster_id='DB-WEST-2').",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-902",
                    title="Failover Decision Schema",
                    text="Emit decision enum ('promoted','aborted'), cluster_id, verified boolean, answer, and citations.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-903",
                    title="Connection String TLS Parameters",
                    text="Enforce sslmode=verify-full on all regional connection URIs.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-904",
                    title="Query Timeout Default Setting",
                    text="OLTP queries carry a 30-second statement_timeout.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-905",
                    title="Vacuum Freeze Threshold",
                    text="Prevent XID wraparound via autovacuum_freeze_max_age.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-TS-901": 2.0, "DOC-TS-902": 1.0},
            expected_claims=[
                "Inspect replication lag on DB-WEST-2 before promoting the replica.",
            ],
            forbidden_claims=["Drop primary WAL archives prior to verifying replica lag."],
            expected_tools=[
                ExpectedToolCall(name="inspect_replication_lag", required_args={"cluster_id": "DB-WEST-2"}),
                ExpectedToolCall(name="promote_replica", required_args={"cluster_id": "DB-WEST-2"}),
            ],
            schema_contract=SchemaContract(
                name="ReplicaFailoverSchema",
                required_fields=["decision", "cluster_id", "verified", "answer", "citations"],
                fields={
                    "decision": FieldConstraint(type="string", enum=["promoted", "aborted"]),
                    "cluster_id": FieldConstraint(type="string", pattern=r"^DB-[A-Z0-9-]+$"),
                    "verified": FieldConstraint(type="boolean"),
                    "answer": FieldConstraint(type="string", min_length=15),
                    "citations": FieldConstraint(type="array", min_length=1),
                },
            ),
        ),
        EvalCaseCreate(
            case_code="TS-10",
            title="Enforce GDPR Subject Erasure Workflow",
            category="compliance-agent",
            query="Execute GDPR erasure for user USR-6402 by verifying signed erasure token and purging PII records.",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-TS-1001",
                    title="PII Erasure Automation Contract",
                    text="Call verify_erasure_token(user_id='USR-6402') first; only once verified may purge_pii_records(user_id='USR-6402') delete customer records.",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-1002",
                    title="GDPR Purge Output Format",
                    text="Return status enum ('purged','rejected'), user_id, verified boolean, answer, and citations.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-1003",
                    title="Marketing Opt-Out Preference Sync",
                    text="Email unsubscribes propagate within 2 hours.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-1004",
                    title="Support Ticket Redaction Guide",
                    text="Strip attachment URLs during ticket archival.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-1005",
                    title="Audit Trail Receipt Retention",
                    text="Keep cryptographic erasure receipts for audit verification.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-TS-1001": 2.0, "DOC-TS-1002": 1.0},
            expected_claims=[
                "Verify the erasure token for USR-6402 before purging PII records.",
            ],
            forbidden_claims=["Purge records immediately without verifying the signed erasure token."],
            expected_tools=[
                ExpectedToolCall(name="verify_erasure_token", required_args={"user_id": "USR-6402"}),
                ExpectedToolCall(name="purge_pii_records", required_args={"user_id": "USR-6402"}),
            ],
            schema_contract=SchemaContract(
                name="GdprPurgeSchema",
                required_fields=["status", "user_id", "verified", "answer", "citations"],
                fields={
                    "status": FieldConstraint(type="string", enum=["purged", "rejected"]),
                    "user_id": FieldConstraint(type="string", pattern=r"^USR-\d+$"),
                    "verified": FieldConstraint(type="boolean"),
                    "answer": FieldConstraint(type="string", min_length=15),
                    "citations": FieldConstraint(type="array", min_length=1),
                },
            ),
        ),
        EvalCaseCreate(
            case_code="TS-11",
            title="Rebalance Hot Kafka Consumer Partition",
            category="infra-agent",
            query="Consumer lag exceeded 250k messages on topic events-ingest. Inspect lag and trigger cooperative rebalance.",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-TS-1101",
                    title="Kafka Lag Mitigation Tool Contract",
                    text="First call inspect_consumer_lag(topic='events-ingest'), then invoke trigger_rebalance(topic='events-ingest', strategy='cooperative_sticky').",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-1102",
                    title="Rebalance Response Schema",
                    text="Output action enum ('rebalanced','skipped'), topic, verified boolean, answer, and citations.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-1103",
                    title="Kafka Topic Retention Hours",
                    text="Raw ingestion topics retain uncompacted segments for 72 hours.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-1104",
                    title="Schema Registry Compatibility Mode",
                    text="Enforce BACKWARD compatibility on Avro schemas.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-1105",
                    title="Producer Batch Linger Setting",
                    text="Set linger.ms=10 and lz4 compression for throughput.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-TS-1101": 2.0, "DOC-TS-1102": 1.0},
            expected_claims=[
                "Inspect consumer lag on events-ingest and trigger a cooperative_sticky rebalance.",
            ],
            forbidden_claims=["Delete the events-ingest topic to clear consumer lag."],
            expected_tools=[
                ExpectedToolCall(name="inspect_consumer_lag", required_args={"topic": "events-ingest"}),
                ExpectedToolCall(name="trigger_rebalance", required_args={"topic": "events-ingest", "strategy": "cooperative_sticky"}),
            ],
            schema_contract=SchemaContract(
                name="KafkaRebalanceSchema",
                required_fields=["action", "topic", "verified", "answer", "citations"],
                fields={
                    "action": FieldConstraint(type="string", enum=["rebalanced", "skipped"]),
                    "topic": FieldConstraint(type="string", min_length=3),
                    "verified": FieldConstraint(type="boolean"),
                    "answer": FieldConstraint(type="string", min_length=15),
                    "citations": FieldConstraint(type="array", min_length=1),
                },
            ),
        ),
        EvalCaseCreate(
            case_code="TS-12",
            title="Throttle Over-Limit Trial Sandbox",
            category="finops-agent",
            query="Trial workspace WS-229 exceeded 100% free compute quota. Fetch usage meter and apply sandbox throttle.",
            corpus_passages=[
                CorpusPassage(
                    doc_id="DOC-TS-1201",
                    title="Trial Sandbox Enforcement Spec",
                    text="Verify usage via fetch_usage_meter(workspace_id='WS-229') before calling throttle_workspace(workspace_id='WS-229', tier='trial_cap').",
                    relevance=2.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-1202",
                    title="Workspace Throttle Contract",
                    text="Return action enum ('throttled','unchanged'), workspace_id, verified boolean, answer, and citations.",
                    relevance=1.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-1203",
                    title="Paid Tier Upgrade Checkout Flow",
                    text="Self-serve upgrades unlock full rate limits immediately.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-1204",
                    title="Trial Sample Dataset Catalog",
                    text="New sandboxes include 3 starter demo suites.",
                    relevance=0.0,
                ),
                CorpusPassage(
                    doc_id="DOC-TS-1205",
                    title="Inactivity Hibernation Notice",
                    text="Sandboxes hibernate after 72 hours without requests.",
                    relevance=0.0,
                ),
            ],
            relevant_docs={"DOC-TS-1201": 2.0, "DOC-TS-1202": 1.0},
            expected_claims=[
                "Fetch usage meter for WS-229 before throttling the workspace at trial_cap.",
            ],
            forbidden_claims=["Charge a credit card automatically on a free trial workspace without consent."],
            expected_tools=[
                ExpectedToolCall(name="fetch_usage_meter", required_args={"workspace_id": "WS-229"}),
                ExpectedToolCall(name="throttle_workspace", required_args={"workspace_id": "WS-229", "tier": "trial_cap"}),
            ],
            schema_contract=SchemaContract(
                name="WorkspaceThrottleSchema",
                required_fields=["action", "workspace_id", "verified", "answer", "citations"],
                fields={
                    "action": FieldConstraint(type="string", enum=["throttled", "unchanged"]),
                    "workspace_id": FieldConstraint(type="string", pattern=r"^WS-\d+$"),
                    "verified": FieldConstraint(type="boolean"),
                    "answer": FieldConstraint(type="string", min_length=15),
                    "citations": FieldConstraint(type="array", min_length=1),
                },
            ),
        ),
    ]


def seed_if_empty(store: VerdictStore) -> None:
    """Populate VerdictStore with 3 evaluation suites (36 cases) and 9 pre-evaluated runs."""
    if store.has_suites():
        return

    suite_defs = [
        {
            "id": "rag-grounding",
            "name": "RAG Grounding & Citation Fidelity",
            "subtitle": "Suite 01 · Atomic Claim Verification & Hallucination Traps",
            "description": (
                "Evaluates retrieved evidence grounding, numeric/SLA consistency, forbidden claim avoidance, "
                "and strict citation JSON formatting across 12 enterprise policy & security golden cases."
            ),
            "primary_focus": "Faithfulness & Citation Schema",
            "policy": GatePolicy(
                suite_id="rag-grounding",
                min_ndcg=0.75,
                min_faithfulness=0.80,
                min_schema_pass=0.90,
                min_tool_f1=0.75,
                max_ndcg_drop=0.05,
                max_faithfulness_drop=0.05,
                max_p95_latency_ms=450.0,
            ),
            "cases": _rag_grounding_cases(),
            "runs": [
                (
                    "run-rg-baseline",
                    "Baseline (Prompt v1 / BM25)",
                    "bm25_only",
                    "verdict-rag-v1",
                    "v1.0-bm25",
                    True,
                    "2026-11-24T09:15:00Z",
                ),
                (
                    "run-rg-candidate",
                    "Candidate (Prompt v2 / Hybrid RRF + Guardrails)",
                    "hybrid_rrf",
                    "verdict-rag-v2",
                    "v2.4-guardrailed",
                    False,
                    "2026-11-25T14:30:00Z",
                ),
                (
                    "run-rg-regression",
                    "Regression Candidate (Unconstrained Prompt v3)",
                    "prompt_unconstrained",
                    "verdict-rag-v3-beta",
                    "v3.0-unconstrained",
                    False,
                    "2026-11-26T08:45:00Z",
                ),
            ],
        },
        {
            "id": "hybrid-retrieval",
            "name": "Hybrid Search & Ranking Quality",
            "subtitle": "Suite 02 · Graded NDCG@5, MRR & Lexical-Semantic Bridging",
            "description": (
                "Tests ranked retrieval quality under graded relevance (rel=2 canonical, rel=1 supporting, "
                "rel=0 keyword distractors) across 12 distributed systems and ML infrastructure RFC queries."
            ),
            "primary_focus": "NDCG@5, MRR & Recall@5",
            "policy": GatePolicy(
                suite_id="hybrid-retrieval",
                min_ndcg=0.78,
                min_faithfulness=0.78,
                min_schema_pass=0.90,
                min_tool_f1=0.75,
                max_ndcg_drop=0.04,
                max_faithfulness_drop=0.05,
                max_p95_latency_ms=420.0,
            ),
            "cases": _hybrid_retrieval_cases(),
            "runs": [
                (
                    "run-hr-baseline",
                    "Baseline (Prompt v1 / BM25)",
                    "bm25_only",
                    "retriever-bm25-v1",
                    "v1.0-lexical",
                    True,
                    "2026-11-24T10:00:00Z",
                ),
                (
                    "run-hr-candidate",
                    "Candidate (Prompt v2 / Hybrid RRF + Guardrails)",
                    "hybrid_rrf",
                    "retriever-hybrid-rrf-v2",
                    "v2.4-rrf-fusion",
                    False,
                    "2026-11-25T15:10:00Z",
                ),
                (
                    "run-hr-regression",
                    "Regression Candidate (Unconstrained Prompt v3)",
                    "prompt_unconstrained",
                    "retriever-skew-v3",
                    "v3.0-unconstrained",
                    False,
                    "2026-11-26T09:10:00Z",
                ),
            ],
        },
        {
            "id": "tool-schema",
            "name": "Tool-Calling & Structured Output Contracts",
            "subtitle": "Suite 03 · Ordered Tool Sequence F1 & Pydantic v2 Contracts",
            "description": (
                "Validates ordered multi-step tool execution, required argument accuracy, and strict raw JSON "
                "adherence to typed Pydantic v2 contracts across 12 FinOps, SRE, and Compliance workflows."
            ),
            "primary_focus": "Schema Pass % & Tool Sequence F1",
            "policy": GatePolicy(
                suite_id="tool-schema",
                min_ndcg=0.72,
                min_faithfulness=0.80,
                min_schema_pass=0.92,
                min_tool_f1=0.85,
                max_ndcg_drop=0.05,
                max_faithfulness_drop=0.05,
                max_p95_latency_ms=500.0,
            ),
            "cases": _tool_schema_cases(),
            "runs": [
                (
                    "run-ts-baseline",
                    "Baseline (Prompt v1 / BM25)",
                    "bm25_only",
                    "agent-strict-v1",
                    "v1.0-baseline",
                    True,
                    "2026-11-24T11:20:00Z",
                ),
                (
                    "run-ts-candidate",
                    "Candidate (Prompt v2 / Hybrid RRF + Guardrails)",
                    "prompt_guardrailed",
                    "agent-guard-v2",
                    "v2.4-tool-graph",
                    False,
                    "2026-11-25T16:40:00Z",
                ),
                (
                    "run-ts-regression",
                    "Regression Candidate (Unconstrained Prompt v3)",
                    "prompt_unconstrained",
                    "agent-cot-v3-beta",
                    "v3.0-unconstrained",
                    False,
                    "2026-11-26T09:35:00Z",
                ),
            ],
        },
    ]

    for sdef in suite_defs:
        store.upsert_suite(
            suite_id=sdef["id"],
            name=sdef["name"],
            subtitle=sdef["subtitle"],
            description=sdef["description"],
            primary_focus=sdef["primary_focus"],
            policy=sdef["policy"],
        )
        saved_cases = [
            store.add_case(
                sdef["id"],
                case_payload,
                case_id=f"case-{case_payload.case_code.lower()}",
            )
            for case_payload in sdef["cases"]
        ]

        for run_id, run_name, pipeline, model_name, prompt_ver, is_base, created_at in sdef["runs"]:
            req = ExecuteRunRequest(
                suite_id=sdef["id"],
                name=run_name,
                pipeline=pipeline,
                model_name=model_name,
                prompt_version=prompt_ver,
            )
            results = [
                evaluate_case_with_pipeline(case=c, run_id=run_id, req=req)
                for c in saved_cases
            ]
            summary = summarize_run_metrics(saved_cases, results)
            run = EvalRun(
                id=run_id,
                suite_id=sdef["id"],
                name=run_name,
                pipeline=pipeline,
                model_name=model_name,
                prompt_version=prompt_ver,
                is_baseline=is_base,
                config={
                    "pipeline": pipeline,
                    "seeded": True,
                },
                metrics=summary,
                created_at=created_at,
            )
            store.save_run(run, results)
