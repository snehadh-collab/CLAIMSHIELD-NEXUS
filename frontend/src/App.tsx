import { useEffect, useMemo, useState } from "react";
import { api, type AiBrief, type ApiMetrics, type AuditAction, type GraphPayload } from "./api";
import {
  Activity,
  AlertTriangle,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleUserRound,
  FileCheck2,
  FileText,
  Filter,
  Focus,
  Layers3,
  Maximize2,
  Minus,
  Network,
  Plus,
  Search,
  Shield,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";

type ClaimFlag = "PHANTOM_BILLING" | "UPCODING" | "IMPOSSIBLE_GEOGRAPHY" | "CLEAN";

type Claim = {
  id: string;
  provider: string;
  npi: string;
  member: string;
  facility: string;
  amount: number;
  cpt: string;
  city: string;
  timestamp: string;
  flag: ClaimFlag;
  score: number;
  confidence: string;
  variance: number;
  caseId?: string;
  reasons?: string[];
  policy: string;
  citation: string;
  brief: string;
};

const DEMO_CLAIMS: Claim[] = [
  {
    id: "CLM-PHB-1048",
    provider: "Dr. Synthetic-A",
    npi: "1999999999",
    member: "GHOST-MEM-9102",
    facility: "FAC001",
    amount: 184400,
    cpt: "99215",
    city: "Austin, TX",
    timestamp: "2026-03-15 11:42",
    flag: "PHANTOM_BILLING",
    score: 0.97,
    confidence: "97.2%",
    variance: 84,
    policy:
      "Billing for unverified or non-enrolled member identifiers violates CMS program integrity guidelines.",
    citation: "Synthetic Policy Doc §4.1",
    brief:
      "Dr. Synthetic-A submitted 38 high-complexity encounters against non-enrolled GHOST-MEM identifiers in a 72-hour window. No eligibility or clinical encounter records were found. Volume is 8.4× the peer baseline, indicating a coordinated phantom billing pattern.",
  },
  {
    id: "CLM-GEO-DEL-0",
    provider: "Dr. Synthetic-B",
    npi: "1888888888",
    member: "MEM000142",
    facility: "FAC002",
    amount: 92800,
    cpt: "97110",
    city: "Delhi, IN",
    timestamp: "2026-03-15 10:30",
    flag: "IMPOSSIBLE_GEOGRAPHY",
    score: 0.94,
    confidence: "94.0%",
    variance: 76,
    policy:
      "Claims occurring in geographically incompatible locations inside the defined travel threshold require immediate review.",
    citation: "FWA Geo-Velocity Rule §7.3",
    brief:
      "The member received services in Chennai at 10:02 and Delhi at 10:30 under Dr. Synthetic-B. The 1,760 km transition implies an impossible velocity. No telehealth modifier is present and the sequence exceeds the provider peer threshold by 6.1σ.",
  },
  {
    id: "CLM-UPC-7741",
    provider: "Dr. Synthetic-C",
    npi: "1777777777",
    member: "MEM000884",
    facility: "FAC001",
    amount: 48200,
    cpt: "99215",
    city: "Phoenix, AZ",
    timestamp: "2026-03-14 16:20",
    flag: "UPCODING",
    score: 0.89,
    confidence: "89.4%",
    variance: 68,
    policy:
      "Level 5 evaluation codes must be supported by high-complexity medical decision-making and complete clinical documentation.",
    citation: "NCD-2026.4 §2",
    brief:
      "Dr. Synthetic-C billed CPT 99215 at four times the regional baseline while associated records support only low-complexity visits. 91% of the provider’s E/M claims use the highest code tier versus a 14% specialty peer median.",
  },
  {
    id: "CLM-PHB-1183",
    provider: "Dr. Synthetic-A",
    npi: "1999999999",
    member: "GHOST-MEM-9244",
    facility: "FAC001",
    amount: 71650,
    cpt: "90837",
    city: "Austin, TX",
    timestamp: "2026-03-14 09:18",
    flag: "PHANTOM_BILLING",
    score: 0.91,
    confidence: "91.8%",
    variance: 71,
    policy:
      "Member eligibility must be verified at the point of service before a claim is submitted for reimbursement.",
    citation: "Synthetic Policy Doc §4.1",
    brief:
      "A second unverified member identifier is connected to Dr. Synthetic-A through repeated behavioral health claims. Service intervals overlap with nine other claims and no member enrollment record exists in the eligibility source.",
  },
  {
    id: "CLM-BASE-5502",
    provider: "Dr. Rivera",
    npi: "1555555555",
    member: "MEM000551",
    facility: "FAC003",
    amount: 1240,
    cpt: "99213",
    city: "Denver, CO",
    timestamp: "2026-03-13 14:05",
    flag: "CLEAN",
    score: 0.08,
    confidence: "8.1%",
    variance: 9,
    policy:
      "No active policy conflict. Claim aligns with member eligibility, coding, and geographic thresholds.",
    citation: "Baseline Controls §1.0",
    brief:
      "The claim falls within expected specialty, cost, and utilization baselines. Member eligibility is current, the service location is consistent, and no related anomaly pattern was identified.",
  },
];

const usd = (n: number) => `$${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;

const DEMO_METRICS: ApiMetrics = {
  total_analyzed: 5170,
  flagged_claims: 4,
  flagged_exposure: 1248500,
  flagged_exposure_pct: 24.1,
  active_patterns: 3,
  high_risk_hubs: 3,
};

const queueTabs = ["All Claims", "Phantom Billing", "Upcoding", "Impossible Geography", "Clean"];
const inspectorTabs = ["Evidence Summary", "Compliance Rules", "Audit Ledger"];

const flagLabel = (flag: ClaimFlag) =>
  flag
    .split("_")
    .map((word) => word[0] + word.slice(1).toLowerCase())
    .join(" ");

function BrandMark() {
  return (
    <div className="brand-mark" aria-hidden="true">
      <Shield fill="currentColor" size={23} strokeWidth={1.8} />
    </div>
  );
}

function MetricCard({
  icon,
  label,
  value,
  note,
  emphasis = "",
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  note: string;
  emphasis?: string;
}) {
  return (
    <article className={`metric-card ${emphasis}`}>
      <div className="metric-label">
        <span>{label}</span>
        {icon}
      </div>
      <div className="metric-value">{value}</div>
      <div className="metric-note">{note}</div>
    </article>
  );
}

function PanelHeader({
  icon,
  title,
  description,
  aside,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  aside?: React.ReactNode;
}) {
  return (
    <div className="panel-header">
      <div className="panel-title">
        <span className="panel-icon">{icon}</span>
        <div>
          <div>{title}</div>
          <span>{description}</span>
        </div>
      </div>
      {aside}
    </div>
  );
}

type GNode = { id: string; label: string; meta: string; type: string; x: number; y: number };

const stripPrefix = (id: string) => id.replace(/^(PROV|MEM|FAC)_/, "");

function layoutLive(claim: Claim, graph: GraphPayload): { nodes: GNode[]; edges: number[][] } | null {
  const center = graph.nodes.find((n) => n.node_type === "PROVIDER" && stripPrefix(n.id) === claim.npi);
  if (!center) return null;
  const focus = new Set([claim.member, claim.facility]);
  const others = graph.nodes
    .filter((n) => n.id !== center.id)
    .sort((a, b) => Number(focus.has(stripPrefix(b.id))) - Number(focus.has(stripPrefix(a.id))))
    .slice(0, 9);
  const nodes: GNode[] = [
    { id: claim.npi, label: center.label, meta: `NPI ${claim.npi}`, type: "provider", x: 350, y: 160 },
    ...others.map((n, i) => {
      const angle = (2 * Math.PI * i) / Math.max(others.length, 1) - Math.PI / 2;
      return {
        id: stripPrefix(n.id),
        label: n.label.length > 16 ? `${n.label.slice(0, 15)}…` : n.label,
        meta: n.node_type === "FACILITY" ? "Facility" : n.node_type === "MEMBER" ? "Member" : "Provider",
        type: n.node_type.toLowerCase(),
        x: 350 + 260 * Math.cos(angle),
        y: 160 + 105 * Math.sin(angle),
      };
    }),
  ];
  const index = new Map(graph.nodes.map((n) => [n.id, stripPrefix(n.id)]));
  const pos = new Map(nodes.map((n, i) => [n.id, i]));
  const seen = new Set<string>();
  const edges: number[][] = [];
  for (const e of graph.edges) {
    const a = pos.get(index.get(e.source) ?? "");
    const b = pos.get(index.get(e.target) ?? "");
    if (a === undefined || b === undefined) continue;
    const key = `${a}-${b}`;
    if (!seen.has(key)) { seen.add(key); edges.push([a, b]); }
  }
  return { nodes, edges };
}

function EntityGraph({
  claim,
  entityType,
  showLabels,
  zoom,
  graph,
}: {
  claim: Claim;
  entityType: string;
  showLabels: boolean;
  zoom: number;
  graph?: GraphPayload | null;
}) {
  const live = graph ? layoutLive(claim, graph) : null;
  const demoNodes: GNode[] = [
    { id: claim.npi, label: claim.provider, meta: `NPI ${claim.npi}`, type: "provider", x: 350, y: 154 },
    { id: claim.member, label: claim.member, meta: "Member", type: "member", x: 156, y: 93 },
    { id: claim.facility, label: claim.facility, meta: claim.city, type: "facility", x: 553, y: 101 },
    { id: "peer-a", label: "Dr. Synthetic-B", meta: "Peer provider", type: "provider", x: 190, y: 256 },
    { id: "peer-b", label: "Dr. Synthetic-C", meta: "Peer provider", type: "provider", x: 500, y: 257 },
    { id: "member-peer", label: "MEM000627", meta: "Related member", type: "member", x: 650, y: 218 },
  ];
  const demoEdges = [
    [0, 1],
    [0, 2],
    [0, 3],
    [0, 4],
    [2, 5],
    [4, 5],
  ];
  const nodes = live ? live.nodes : demoNodes;
  const edges = live ? live.edges : demoEdges;
  const focusedIds = new Set([claim.npi, claim.member, claim.facility]);
  const typeVisible = (type: string) =>
    entityType === "All entities" ||
    entityType.toLowerCase().startsWith(type === "facility" ? "facilit" : type);

  return (
    <div className="graph-canvas">
      <svg viewBox="0 0 700 320" role="img" aria-label={`Entity network focused on ${claim.id}`}>
        <g className="graph-stage" transform={`translate(${350 * (1 - zoom)} ${160 * (1 - zoom)}) scale(${zoom})`}>
          {edges.map(([start, end]) => {
            const related = focusedIds.has(nodes[start].id) && focusedIds.has(nodes[end].id);
            return (
              <line
                className={`edge ${related ? "focused" : "muted"}`}
                key={`${start}-${end}`}
                x1={nodes[start].x}
                x2={nodes[end].x}
                y1={nodes[start].y}
                y2={nodes[end].y}
              />
            );
          })}
          {nodes.map((node) => {
            const focused = focusedIds.has(node.id);
            return (
              <g
                className={`node ${node.type} ${focused ? "focused" : "muted"} ${
                  typeVisible(node.type) ? "" : "filtered"
                }`}
                key={node.id}
              >
                <circle className="node-ring" cx={node.x} cy={node.y} r={focused ? 20 : 15} />
                <circle className="node-core" cx={node.x} cy={node.y} r={focused ? 8 : 6} />
                {showLabels && (
                  <g className="node-label">
                    <text className="node-name" x={node.x} y={node.y + 31} textAnchor="middle">
                      {node.label}
                    </text>
                    <text className="node-meta" x={node.x} y={node.y + 43} textAnchor="middle">
                      {node.meta}
                    </text>
                  </g>
                )}
              </g>
            );
          })}
        </g>
      </svg>
      <div className="graph-summary">
        <span>Focused relationship</span>
        <strong>{claim.provider}</strong>
        <small>{claim.member} · {claim.facility}</small>
      </div>
      <div className="graph-legend">
        <span><i className="provider-dot" /> Provider</span>
        <span><i className="member-dot" /> Member</span>
        <span><i className="facility-dot" /> Facility</span>
      </div>
    </div>
  );
}

function BaselineChart({ claim }: { claim: Claim }) {
  const claimLevel = Math.max(12, claim.variance);
  return (
    <div className="baseline-chart">
      <div className="chart-heading">
        <span>Peer baseline variance</span>
        <strong>{claim.flag === "CLEAN" ? "Within range" : `${(claim.variance / 10).toFixed(1)}× above`}</strong>
      </div>
      <div className="bar-row">
        <span>Selected claim</span>
        <div><i className="claim-bar" style={{ width: `${claimLevel}%` }} /></div>
        <strong>{claimLevel}</strong>
      </div>
      <div className="bar-row">
        <span>Peer median</span>
        <div><i className="peer-bar" style={{ width: "22%" }} /></div>
        <strong>22</strong>
      </div>
      <div className="chart-scale"><span>0</span><span>Normalized variance index</span><span>100</span></div>
    </div>
  );
}

export default function App() {
  const [claims, setClaims] = useState<Claim[]>(DEMO_CLAIMS);
  const [metrics, setMetrics] = useState<ApiMetrics>(DEMO_METRICS);
  const [source, setSource] = useState<"loading" | "live" | "demo">("loading");
  const [graph, setGraph] = useState<GraphPayload | null>(null);
  const [audit, setAudit] = useState<AuditAction[]>([]);
  const [aiBrief, setAiBrief] = useState<AiBrief | null>(null);
  const [briefLoading, setBriefLoading] = useState(false);
  const [selectedId, setSelectedId] = useState(DEMO_CLAIMS[0].id);
  const [activeQueueTab, setActiveQueueTab] = useState("All Claims");
  const [inspectorTab, setInspectorTab] = useState("Evidence Summary");
  const [search, setSearch] = useState("");
  const [showLabels, setShowLabels] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [entityType, setEntityType] = useState("All entities");
  const [caseState, setCaseState] = useState<"idle" | "approved" | "dismissed">("idle");

  const selected = claims.find((claim) => claim.id === selectedId) || claims[0];
  const caseKey = selected.caseId ?? selected.id;

  useEffect(() => {
    let cancelled = false;
    api
      .dashboard()
      .then((d) => {
        if (cancelled || d.cases.length === 0) return;
        const mapped: Claim[] = d.cases.map((c) => ({
          id: c.claim_id,
          caseId: c.id,
          provider: c.provider,
          npi: c.npi,
          member: c.member,
          facility: c.facility,
          amount: c.amount,
          cpt: c.cpt,
          city: c.city,
          timestamp: c.timestamp,
          flag: c.flag,
          score: c.score,
          confidence: `${(c.confidence * 100).toFixed(1)}%`,
          variance: c.variance,
          policy: c.policy,
          citation: c.citation,
          brief: c.brief,
          reasons: c.flag_reasons,
        }));
        setClaims(mapped);
        setMetrics(d.metrics);
        setSelectedId(mapped[0].id);
        setSource("live");
      })
      .catch(() => !cancelled && setSource("demo"));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (source !== "live") return;
    let cancelled = false;
    setGraph(null);
    api.graph(selected.npi).then((g) => !cancelled && setGraph(g)).catch(() => !cancelled && setGraph(null));
    return () => {
      cancelled = true;
    };
  }, [source, selected.npi]);

  useEffect(() => {
    if (source !== "live") return;
    let cancelled = false;
    setAudit([]);
    api.audit(caseKey).then((r) => !cancelled && setAudit(r.actions)).catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [source, caseKey]);
  const visibleClaims = useMemo(() => {
    const normalized = search.toLowerCase();
    return claims.filter((claim) => {
      const tabMatch = activeQueueTab === "All Claims" || flagLabel(claim.flag) === activeQueueTab;
      const searchMatch = [
        claim.id,
        claim.provider,
        claim.npi,
        claim.member,
        claim.facility,
      ].some((value) => value.toLowerCase().includes(normalized));
      return tabMatch && searchMatch;
    });
  }, [activeQueueTab, search]);

  const chooseClaim = (claim: Claim) => {
    setSelectedId(claim.id);
    setCaseState("idle");
    setAiBrief(null);
    setInspectorTab("Evidence Summary");
  };

  const decide = (state: "approved" | "dismissed") => {
    setCaseState(state);
    if (source !== "live") return;
    api
      .recordAction(caseKey, state === "approved" ? "APPROVE" : "DISMISS", `Decision by investigator from SIU workspace`)
      .then((a) => setAudit((prev) => [...prev, a]))
      .catch(() => undefined);
  };

  const generateBrief = () => {
    setBriefLoading(true);
    api
      .brief(caseKey, selected.brief, selected.reasons?.length ? selected.reasons : [selected.flag])
      .then(setAiBrief)
      .catch(() => setAiBrief(null))
      .finally(() => setBriefLoading(false));
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <BrandMark />
          <div className="brand-copy">
            <div><strong>Acentra Health</strong><span>ClaimShield Nexus</span></div>
            <small>FWA Intelligence Suite</small>
          </div>
        </div>

        <label className="global-search">
          <Search size={15} />
          <input
            aria-label="Search claims, providers, or members"
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search claims, providers, or members"
            value={search}
          />
          <kbd>⌘K</kbd>
        </label>

        <div className="engine-status">
          <span className="status-dot" />
          <div>
            <strong>Data Engine: {source === "live" ? "Connected" : source === "loading" ? "Connecting…" : "Demo data (API offline)"}</strong>
            <small>{metrics.total_analyzed.toLocaleString()} claims analyzed</small>
          </div>
        </div>
        <button className="profile-button" type="button">
          <span className="avatar">AL</span>
          <span><strong>Acentra Lead</strong><small>Investigator</small></span>
          <ChevronDown size={14} />
        </button>
      </header>

      <div className="dashboard">
        <div className="page-heading">
          <div>
            <span>ClaimShield Nexus</span>
            <h1>Special Investigations Unit (SIU) Workspace</h1>
            <p>Prioritized claims, connected entities, and grounded compliance evidence.</p>
          </div>
          <div className="ledger-status">
            <FileCheck2 size={15} />
            <span>Investigation Audit Ledger</span>
            <strong>Current</strong>
          </div>
        </div>

        <section className="metrics-grid" aria-label="Claims overview">
          <MetricCard icon={<FileText size={18} />} label="Total analyzed" note={`${metrics.flagged_claims.toLocaleString()} claims flagged`} value={metrics.total_analyzed.toLocaleString()} />
          <MetricCard
            emphasis="highlight"
            icon={<AlertTriangle size={18} />}
            label="Flagged exposure"
            note={`${metrics.flagged_exposure_pct}% of analyzed value`}
            value={usd(metrics.flagged_exposure)}
          />
          <MetricCard icon={<Activity size={18} />} label="Active fraud patterns" note={`${metrics.active_patterns} detection classes`} value={String(metrics.active_patterns)} />
          <MetricCard icon={<Network size={18} />} label="High-risk hubs" note="Provider degree-centrality hubs" value={String(metrics.high_risk_hubs)} />
        </section>

        <section className="workspace-grid">
          <div className="left-workspace">
            <article className="panel graph-panel">
              <PanelHeader
                aside={<span className="connected-chip"><span /> Live network</span>}
                description="Provider, member, and facility relationships"
                icon={<Network size={17} />}
                title="Entity Topology Graph"
              />
              <div className="graph-toolbar">
                <div className="control-group">
                  <button aria-label="Zoom out" onClick={() => setZoom(Math.max(0.85, zoom - 0.1))} type="button"><Minus size={14} /></button>
                  <span>{Math.round(zoom * 100)}%</span>
                  <button aria-label="Zoom in" onClick={() => setZoom(Math.min(1.15, zoom + 0.1))} type="button"><Plus size={14} /></button>
                  <button aria-label="Reset zoom" onClick={() => setZoom(1)} type="button"><Maximize2 size={14} /></button>
                </div>
                <button
                  className={`toolbar-button ${showLabels ? "active" : ""}`}
                  onClick={() => setShowLabels(!showLabels)}
                  type="button"
                >
                  <Layers3 size={14} /> Labels
                </button>
                <label className="entity-select">
                  <Filter size={13} />
                  <select value={entityType} onChange={(event) => setEntityType(event.target.value)}>
                    <option>All entities</option>
                    <option>Providers</option>
                    <option>Members</option>
                    <option>Facilities</option>
                  </select>
                </label>
              </div>
              <EntityGraph claim={selected} entityType={entityType} graph={graph} showLabels={showLabels} zoom={zoom} />
            </article>

            <article className="panel queue-panel">
              <PanelHeader
                aside={
                  <div className="queue-summary">
                    <span><i className="critical-dot" /> {claims.filter((c) => c.score >= 0.7).length} critical</span>
                    <span><i className="review-dot" /> {claims.filter((c) => c.score < 0.7 && c.flag !== "CLEAN").length} review</span>
                  </div>
                }
                description="Prioritized by rules engine and anomaly score"
                icon={<Activity size={17} />}
                title="Anomaly Detection Claims Queue"
              />
              <div className="tabs queue-tabs" role="tablist" aria-label="Claim filters">
                {queueTabs.map((tab) => (
                  <button
                    aria-selected={activeQueueTab === tab}
                    className={activeQueueTab === tab ? "active" : ""}
                    key={tab}
                    onClick={() => setActiveQueueTab(tab)}
                    role="tab"
                    type="button"
                  >
                    {tab}
                    <span>{tab === "All Claims" ? claims.length : claims.filter((c) => flagLabel(c.flag) === tab).length}</span>
                  </button>
                ))}
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Claim</th>
                      <th>Provider</th>
                      <th>Member / Facility</th>
                      <th>Exposure</th>
                      <th>Detection</th>
                      <th>Anomaly</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleClaims.map((claim) => (
                      <tr
                        className={claim.id === selected.id ? "selected" : ""}
                        key={claim.id}
                        onClick={() => chooseClaim(claim)}
                      >
                        <td><strong className="claim-id">{claim.id}</strong><small>{claim.timestamp}</small></td>
                        <td><strong>{claim.provider}</strong><small>NPI {claim.npi}</small></td>
                        <td>
                          <strong className={claim.member.includes("GHOST") ? "ghost-id" : ""}>{claim.member}</strong>
                          <small>{claim.facility} · {claim.city}</small>
                        </td>
                        <td><strong>{usd(claim.amount)}</strong><small>CPT {claim.cpt}</small></td>
                        <td><span className={`flag ${claim.flag.toLowerCase()}`}>{flagLabel(claim.flag)}</span></td>
                        <td>
                          <div className="score-cell">
                            <div className="score-track"><span style={{ width: `${claim.score * 100}%` }} /></div>
                            <strong>{claim.score.toFixed(2)}</strong>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {visibleClaims.length === 0 && <div className="empty-state"><Search size={18} />No claims match the current filters.</div>}
              </div>
              <div className="table-footer">
                <span>Showing {visibleClaims.length} of {metrics.total_analyzed.toLocaleString()} claims</span>
                <span><CircleUserRound size={13} /> {source === "live" ? "Scored by rules, ML and graph engines" : "Sample data"}</span>
              </div>
            </article>
          </div>

          <aside className="panel inspector-panel">
            <PanelHeader
              aside={<span className={`risk-chip ${selected.flag.toLowerCase()}`}>{flagLabel(selected.flag)}</span>}
              description="Evidence, policy context, and disposition"
              icon={<ShieldCheck size={17} />}
              title="Case Inspector & Brief Console"
            />
            <div className="case-identity">
              <div>
                <span>Selected case</span>
                <strong>{selected.id}</strong>
                <small>{selected.provider} · NPI {selected.npi}</small>
              </div>
              <div className="confidence">
                <strong>{selected.confidence}</strong>
                <span>Confidence</span>
              </div>
            </div>

            <div className="tabs inspector-tabs" role="tablist" aria-label="Case inspector sections">
              {inspectorTabs.map((tab) => (
                <button
                  aria-selected={inspectorTab === tab}
                  className={inspectorTab === tab ? "active" : ""}
                  key={tab}
                  onClick={() => setInspectorTab(tab)}
                  role="tab"
                  type="button"
                >
                  {tab}
                </button>
              ))}
            </div>

            <div className="inspector-content">
              {inspectorTab === "Evidence Summary" && (
                <>
                  <section className="content-section">
                    <div className="section-label"><Focus size={14} /> Executive investigation brief</div>
                    <p>{selected.brief}</p>
                    {source === "live" && (
                      <button className="secondary-action" disabled={briefLoading} onClick={generateBrief} type="button">
                        <Sparkles size={14} /> {briefLoading ? "Generating…" : "Generate AI copilot brief"}
                      </button>
                    )}
                  </section>
                  {aiBrief && (
                    <section className="content-section">
                      <div className="section-label"><Sparkles size={14} /> AI copilot brief · {Math.round(aiBrief.confidence_score * 100)}% confidence</div>
                      <p>{aiBrief.executive_summary}</p>
                      <p><strong>Recommended action:</strong> {aiBrief.recommended_action}</p>
                    </section>
                  )}
                  <BaselineChart claim={selected} />
                  <div className="evidence-grid">
                    <div><span>Risk class</span><strong>{flagLabel(selected.flag)}</strong></div>
                    <div><span>Exposure</span><strong>{usd(selected.amount)}</strong></div>
                    <div><span>Model score</span><strong>{selected.score.toFixed(2)} / 1.00</strong></div>
                    <div><span>Facility</span><strong>{selected.facility}</strong></div>
                  </div>
                </>
              )}

              {inspectorTab === "Compliance Rules" && (
                <>
                  <section className="content-section policy-section">
                    <div className="section-label"><FileText size={14} /> Grounded compliance rules</div>
                    <blockquote>“{selected.policy}”</blockquote>
                    <div className="citation"><CheckCircle2 size={13} /> [{selected.citation}]</div>
                  </section>
                  <div className="rule-metadata">
                    <div><span>Source status</span><strong>Verified</strong></div>
                    <div><span>Retrieval confidence</span><strong>{selected.confidence}</strong></div>
                    <div><span>Control family</span><strong>CMS Program Integrity</strong></div>
                  </div>
                </>
              )}

              {inspectorTab === "Audit Ledger" && (
                <div className="audit-ledger">
                  {audit.map((a, i) => (
                    <div key={`${a.timestamp}-${i}`}><span className="audit-mark" /><section><strong>Decision: {a.action}</strong><small>{a.investigator_id} · {new Date(a.timestamp).toLocaleString()}</small></section></div>
                  ))}
                  <div><span className="audit-mark" /><section><strong>Case opened for review</strong><small>Automated triage · 10:43:18 UTC</small></section></div>
                  <div><span className="audit-mark" /><section><strong>Policy evidence retrieved</strong><small>{selected.citation} · 10:43:19 UTC</small></section></div>
                  <div><span className="audit-mark current" /><section><strong>Awaiting investigator decision</strong><small>Acentra Lead Investigator · Current</small></section></div>
                </div>
              )}
            </div>

            <div className="decision-panel">
              <div className="decision-heading"><span>Human decision</span><small>Required to change case status</small></div>
              {caseState !== "idle" && (
                <div className={`case-message ${caseState}`}>
                  {caseState === "approved" ? <Check size={14} /> : <X size={14} />}
                  {caseState === "approved" ? "Routed to SIU investigation" : "Dismissed as false positive"}
                </div>
              )}
              <button className="primary-action" onClick={() => decide("approved")} type="button">
                <ShieldCheck size={16} /> Approve SIU Investigation
              </button>
              <button className="secondary-action" onClick={() => decide("dismissed")} type="button">
                Dismiss False Positive
              </button>
              <div className="audit-note"><Shield size={12} /> Decision recorded in Investigation Audit Ledger</div>
            </div>
          </aside>
        </section>
      </div>
    </main>
  );
}
