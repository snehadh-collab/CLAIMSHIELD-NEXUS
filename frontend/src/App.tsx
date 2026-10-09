import { useEffect, useMemo, useState } from "react";
import { api, type InvestigatorAction, type QueueCase } from "./services/api";
import SandboxView from "./components/SandboxView";
import FinancialForecastView from "./components/FinancialForecastView";
import CaseWorkspaceView from "./components/CaseWorkspaceView";

type Page = "command" | "case" | "provider" | "analyzer" | "brain" | "audit" | "brief" | "personal" | "access" | "regions" | "assignments" | "alerts" | "digest";
type IconName =
  | "grid" | "case" | "provider" | "scan" | "brain" | "audit" | "search"
  | "bell" | "chevron" | "more" | "refresh" | "filter" | "arrow" | "shield"
  | "spark" | "copy" | "download" | "plus" | "check" | "x" | "clock" | "network";

const demoCases: QueueCase[] = [
  { id: "CASE-001", title: "High-Dollar Coordinated Fraud Ring", provider: "Dr. Alex Mercer", npi: "1029384", billed: "$842,650", risk: 87, flag: "Network collusion", status: "Under Review", updated: "2 min ago" },
  { id: "CASE-002", title: "CPT Upcoding Violation", provider: "Northstar Family Care", npi: "1184726", billed: "$218,420", risk: 64, flag: "CPT upcoding", status: "Pending Records", updated: "18 min ago" },
  { id: "CASE-003", title: "Clean / False Positive", provider: "Lakeside Pediatrics", npi: "1538204", billed: "$42,180", risk: 18, flag: "Billing velocity", status: "Triage", updated: "1 hr ago" },
  { id: "CASE-004", title: "Duplicate Billing Cluster", provider: "Apex Diagnostic Lab", npi: "1800291", billed: "$386,210", risk: 76, flag: "Duplicate billing", status: "Escalated", updated: "3 hrs ago" },
  { id: "CASE-005", title: "Impossible Geography Pattern", provider: "MetroCare Associates", npi: "1438207", billed: "$294,880", risk: 72, flag: "Impossible geography", status: "Under Review", updated: "4 hrs ago" },
  { id: "CASE-006", title: "Unbundling Review", provider: "Hudson Surgical Group", npi: "1629403", billed: "$176,540", risk: 58, flag: "Procedure unbundling", status: "Pending Records", updated: "5 hrs ago" },
  { id: "CASE-007", title: "Referral Network Anomaly", provider: "Beacon Imaging Center", npi: "1742058", billed: "$512,300", risk: 81, flag: "Referral concentration", status: "Escalated", updated: "Yesterday" },
  { id: "CASE-008", title: "Modifier Misuse Review", provider: "Park Avenue Orthopedics", npi: "1094725", billed: "$98,720", risk: 46, flag: "Modifier misuse", status: "Triage", updated: "Yesterday" },
  { id: "CASE-009", title: "Phantom Billing Indicators", provider: "Summit Home Health", npi: "1285049", billed: "$634,900", risk: 89, flag: "Phantom billing", status: "Under Review", updated: "2 days ago" },
  { id: "CASE-010", title: "Excessive Service Frequency", provider: "Eastside Rehabilitation", npi: "1950274", billed: "$143,600", risk: 55, flag: "Service frequency", status: "Pending Records", updated: "2 days ago" },
  { id: "CASE-011", title: "Provider Identity Review", provider: "Union Primary Care", npi: "1573048", billed: "$72,410", risk: 34, flag: "Identity mismatch", status: "Triage", updated: "3 days ago" },
  { id: "CASE-012", title: "Coordinated DME Billing", provider: "Atlantic Medical Supply", npi: "1836502", billed: "$448,260", risk: 79, flag: "DME network pattern", status: "Escalated", updated: "3 days ago" },
];

const nav: { page: Page; label: string; icon: IconName }[] = [
  { page: "command", label: "SIU Command Center", icon: "grid" },
  { page: "case", label: "Case Investigation", icon: "case" },
  { page: "provider", label: "Provider Intelligence", icon: "provider" },
  { page: "analyzer", label: "Claim Analyzer", icon: "scan" },
  { page: "brain", label: "Deep-Dive Workspace", icon: "brain" },
  { page: "audit", label: "Audit Trail", icon: "audit" },
];

function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  const paths: Record<IconName, React.ReactNode> = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></>,
    case: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 5V3h8v2M3 11h18M10 14h4"/></>,
    provider: <><circle cx="12" cy="8" r="4"/><path d="M4 21c.8-5 3.5-7 8-7s7.2 2 8 7"/></>,
    scan: <><path d="M8 3H4a1 1 0 0 0-1 1v4M16 3h4a1 1 0 0 1 1 1v4M8 21H4a1 1 0 0 1-1-1v-4M16 21h4a1 1 0 0 0 1-1v-4M7 12h10"/></>,
    brain: <><path d="M9 4a3 3 0 0 0-5 2v2a3 3 0 0 0 0 5v2a3 3 0 0 0 5 3M15 4a3 3 0 0 1 5 2v2a3 3 0 0 1 0 5v2a3 3 0 0 1-5 3M9 4v16M15 4v16M9 8h3M12 14h3"/></>,
    audit: <><path d="M6 3h12v18H6zM9 8h6M9 12h6M9 16h4"/><path d="M9 3V1h6v2"/></>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></>,
    chevron: <path d="m9 18 6-6-6-6"/>,
    more: <><circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/></>,
    refresh: <><path d="M20 11a8 8 0 1 0-2 5.3"/><path d="M20 4v7h-7"/></>,
    filter: <path d="M3 5h18l-7 8v6l-4 2v-8z"/>,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6"/></>,
    shield: <><path d="M12 2 4 5v6c0 5 3.5 9 8 11 4.5-2 8-6 8-11V5z"/><path d="m8.5 12 2.2 2.2 4.8-5"/></>,
    spark: <path d="m12 2 1.6 5.4L19 9l-5.4 1.6L12 16l-1.6-5.4L5 9l5.4-1.6zM19 16l.7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7z"/>,
    copy: <><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V4H4v12h4"/></>,
    download: <><path d="M12 3v12M7 10l5 5 5-5M4 21h16"/></>,
    plus: <><path d="M12 5v14M5 12h14"/></>,
    check: <path d="m5 12 4 4L19 6"/>,
    x: <><path d="m6 6 12 12M18 6 6 18"/></>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/></>,
    network: <><circle cx="12" cy="5" r="3"/><circle cx="5" cy="18" r="3"/><circle cx="19" cy="18" r="3"/><path d="m10 8-4 7M14 8l4 7M8 18h8"/></>,
  };
  return <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

function Brand({ compact = false }: { compact?: boolean }) {
  return <div className="brand"><span className="brand-mark" aria-label="A Health">
    <svg viewBox="0 0 48 44" role="img" aria-hidden="true">
      <defs>
        <linearGradient id="brand-arch" x1="8" y1="35" x2="35" y2="4" gradientUnits="userSpaceOnUse">
          <stop stopColor="#80DD47"/>
          <stop offset="1" stopColor="#19B941"/>
        </linearGradient>
        <linearGradient id="brand-swoop" x1="7" y1="35" x2="42" y2="35" gradientUnits="userSpaceOnUse">
          <stop stopColor="#A5E84D"/>
          <stop offset="1" stopColor="#54CB44"/>
        </linearGradient>
      </defs>
      <path d="M9 30.5 20.4 8.8c1.8-3.4 6.6-3.7 8.7-.5L42 28.1c1.3 2 .3 4.7-2.1 5.3l-5.1 1.2-9.6-15.7a1.7 1.7 0 0 0-2.9.1l-6.1 12.1L9 30.5Z" fill="url(#brand-arch)"/>
      <path d="M7.2 32.6c7.4-4.4 16.3-6.1 24.8-3.9 3.5.9 6.7 2.4 9.4 4.5l-2.8 6.1c-8.4-5.7-19.6-6-28.5-.7a3.5 3.5 0 0 1-4.9-1.5 3.5 3.5 0 0 1 2-4.5Z" fill="url(#brand-swoop)"/>
    </svg>
  </span>{!compact && <span><b>A Health</b><small>ClaimShield Nexus</small></span>}</div>;
}

function Button({ children, variant = "secondary", icon, trailingIcon, onClick, disabled, loading, className = "" }: {
  children: React.ReactNode; variant?: "primary" | "secondary" | "danger" | "ghost";
  icon?: IconName; trailingIcon?: IconName; onClick?: () => void; disabled?: boolean; loading?: boolean; className?: string;
}) {
  return <button className={`btn btn-${variant} ${className}`} onClick={onClick} disabled={disabled || loading}>
    {loading ? <span className="spinner"/> : icon && <Icon name={icon} size={16}/>}<span>{loading ? "Processing…" : children}</span>{!loading && trailingIcon && <Icon name={trailingIcon} size={16}/>}
  </button>;
}

function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "critical" | "warning" | "success" | "info" | "purple" | "neutral" }) {
  return <span className={`badge badge-${tone}`}><span className="badge-dot"/>{children}</span>;
}

function RiskBadge({ risk }: { risk: number }) {
  return <Badge tone={risk >= 70 ? "critical" : risk >= 40 ? "warning" : "success"}>{risk >= 70 ? "CRITICAL" : risk >= 40 ? "MODERATE" : "LOW"} · {risk}%</Badge>;
}

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <section className={`card ${className}`}>{children}</section>;
}

function Login({ onLogin }: { onLogin: () => void }) {
  const [loading, setLoading] = useState(false);
  const login = () => { setLoading(true); setTimeout(onLogin, 750); };
  return <main className="login-page">
    <div className="login-orb orb-one"/><div className="login-orb orb-two"/>
    <div className="login-brand"><Brand/><Badge tone="success">SECURE SIU ENVIRONMENT</Badge></div>
    <Card className="login-card">
      <div className="login-icon"><Icon name="shield" size={30}/></div>
      <p className="eyebrow">INVESTIGATOR ACCESS</p>
      <h1>Welcome to ClaimShield Nexus</h1>
      <p className="muted">AI-powered fraud, waste and abuse investigation for A Health.</p>
      <label className="field-label">Work email</label>
      <div className="input">maya.chen@ahealthcentre.org</div>
      <label className="field-label">Password</label>
      <div className="input password">•••••••••••• <span>SHOW</span></div>
      <div className="login-options"><label><input type="checkbox" defaultChecked/> Keep me signed in</label><button className="text-button">Forgot access?</button></div>
      <Button variant="primary" onClick={login} loading={loading} trailingIcon="arrow" className="full">Enter secure portal</Button>
      <div className="secure-note"><Icon name="shield" size={15}/> Protected by enterprise SSO · HIPAA-aligned session</div>
    </Card>
    <p className="login-footer">A Health | ClaimShield Nexus · BUILD TO CARE · Authorized personnel only · v3.5.0</p>
  </main>;
}

function Sidebar({ page, setPage, collapsed, onCollapse }: { page: Page; setPage: (p: Page) => void; collapsed: boolean; onCollapse: () => void }) {
  return <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
    <div className="sidebar-brand"><Brand compact={collapsed}/></div>
    <nav aria-label="Primary navigation">{nav.map(item =>
      <button key={item.page} className={`nav-item ${page === item.page ? "active" : ""}`} onClick={() => setPage(item.page)} title={item.label}>
        <Icon name={item.icon}/>{!collapsed && <span>{item.label}</span>}
      </button>
    )}</nav>
    <div className="sidebar-bottom">
      {!collapsed && <div className="engine-card"><div className="engine-title"><span className="pulse"/> ENGINE ACTIVE</div><strong>Protection runtime</strong><small>v3.5.0 · All systems nominal</small></div>}
      <button className="collapse-btn" onClick={onCollapse}><Icon name="chevron"/>{!collapsed && "Collapse navigation"}</button>
    </div>
  </aside>;
}

function Header({ title, onSearch, onSignOut, onNavigate, connected }: { title: string; onSearch: () => void; onSignOut: () => void; onNavigate: (page: Page) => void; connected: boolean }) {
  const [profileOpen,setProfileOpen]=useState(false);
  const [notificationOpen,setNotificationOpen]=useState(false);
  const [readNotifications,setReadNotifications]=useState<Set<number>>(new Set());
  const notifications=[
    {title:"Critical case assigned",detail:"CASE-001 · High-Dollar Coordinated Fraud Ring",time:"2 min ago",tone:"critical",page:"case" as Page},
    {title:"Medical records received",detail:"CASE-002 · 14 documents are ready for review",time:"18 min ago",tone:"info",page:"case" as Page},
    {title:"Knowledge vault updated",detail:"Provider intelligence synthesis completed",time:"1 hr ago",tone:"purple",page:"audit" as Page},
  ];
  const navigate=(page:Page)=>{onNavigate(page);setProfileOpen(false);setNotificationOpen(false)};
  const openNotification=(index:number,page:Page)=>{setReadNotifications(current=>new Set(current).add(index));navigate(page)};
  return <header className="topbar">
    <div><p className="crumb">A HEALTH | CLAIMSHIELD NEXUS</p><h1>{title}</h1></div>
    <div className="header-actions">
      <button className="global-search" onClick={onSearch}><Icon name="search"/><span>Search cases, providers, claims…</span><span className="search-submit"><Icon name="search" size={14}/></span></button>
      <div className="build-slogan">BUILD TO CARE</div>
      <div className={`system-pill ${connected ? "" : "offline"}`}><span className="pulse"/> <span><b>{connected ? "ENGINE ACTIVE" : "DEMO MODE"}</b><small>v3.5.0 · {connected ? "Context ready" : "API unavailable"}</small></span></div>
      <div className="notification-wrap">
        <button className={`icon-button ${notificationOpen?"active":""}`} aria-label="Notifications" aria-expanded={notificationOpen} onClick={()=>{setNotificationOpen(!notificationOpen);setProfileOpen(false)}}><Icon name="bell"/>{readNotifications.size<notifications.length&&<span className="notification-dot"/>}</button>
        {notificationOpen&&<div className="notification-menu">
          <div className="notification-head"><div><p>NOTIFICATIONS</p><h3>Investigation updates</h3></div><button onClick={()=>setReadNotifications(new Set(notifications.map((_,index)=>index)))}>Mark all read</button></div>
          <div className="notification-list">{notifications.map((notification,index)=><button className={readNotifications.has(index)?"read":""} key={notification.title} onClick={()=>openNotification(index,notification.page)}><span className={`notification-icon notification-${notification.tone}`}><Icon name={index===0?"shield":index===1?"case":"brain"} size={16}/></span><span><b>{notification.title}</b><small>{notification.detail}</small><time>{notification.time}</time></span>{!readNotifications.has(index)&&<i/>}</button>)}</div>
          <button className="notification-footer" onClick={()=>navigate("assignments")}>Manage notification preferences <Icon name="chevron" size={13}/></button>
        </div>}
      </div>
      <div className="profile-menu-wrap">
        <button className={`profile ${profileOpen?"open":""}`} onClick={()=>{setProfileOpen(!profileOpen);setNotificationOpen(false)}} aria-expanded={profileOpen} aria-haspopup="menu"><span className="avatar">MC</span><span><b>Maya Chen</b><small>Senior Investigator</small></span><Icon name="chevron" size={14}/></button>
        {profileOpen&&<div className="profile-menu" role="menu">
          <div className="profile-menu-head"><span className="avatar">MC</span><span><b>Maya Chen</b><small>maya.chen@ahealthcentre.org</small></span></div>
          <div className="profile-menu-meta"><span>Senior SIU Investigator</span><Badge tone="success">ACTIVE</Badge></div>
          <div className="profile-menu-item" role="menuitem" tabIndex={0}><Icon name="provider"/><span><b>Investigator profile</b><small>Credentials and assigned regions</small></span><Icon name="chevron" size={14}/>
            <div className="profile-submenu" role="menu"><p>INVESTIGATOR PROFILE</p><button role="menuitem" onClick={()=>navigate("personal")}>Personal information<small>Name, contact and investigator ID</small></button><button role="menuitem" onClick={()=>navigate("access")}>Credentials & access<small>Role, permissions and certifications</small></button><button role="menuitem" onClick={()=>navigate("regions")}>Assigned regions<small>New York · Northeast SIU</small></button></div>
          </div>
          <div className="profile-menu-item" role="menuitem" tabIndex={0}><Icon name="bell"/><span><b>Notification preferences</b><small>Alerts and case assignments</small></span><Icon name="chevron" size={14}/>
            <div className="profile-submenu" role="menu"><p>NOTIFICATIONS</p><button role="menuitem" onClick={()=>navigate("assignments")}>Case assignments<small>New and reassigned investigations</small></button><button role="menuitem" onClick={()=>navigate("alerts")}>Critical-risk alerts<small>Immediate fraud-ring notifications</small></button><button role="menuitem" onClick={()=>navigate("digest")}>Daily digest<small>Queue and exposure summary</small></button></div>
          </div>
          <button className="profile-signout" role="menuitem" onClick={onSignOut}><Icon name="x"/><span><b>Sign out</b><small>End this secure session</small></span></button>
        </div>}
      </div>
    </div>
  </header>;
}

function Kpi({ label, value, trend, tone, icon }: { label: string; value: string; trend: string; tone: string; icon: IconName }) {
  return <Card className={`kpi kpi-${tone}`}>
    <div className="kpi-top"><span className="kpi-icon"><Icon name={icon}/></span><span className="mini-trend">{trend}</span></div>
    <strong>{value}</strong><span>{label}</span><small>vs. previous 30 days</small>
  </Card>;
}

function CommandCenter({ openCase, openAction, cases, selectedCase, onSelectCase }: { openCase: (caseItem:QueueCase) => void; openAction: (action: string) => void; cases: QueueCase[]; selectedCase:QueueCase; onSelectCase:(caseItem:QueueCase)=>void }) {
  const [query, setQuery] = useState("");
  const [riskFilter, setRiskFilter] = useState("All risk");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set([selectedCase.id]));
  const filtered = cases.filter(c => (`${c.id} ${c.provider} ${c.npi} ${c.flag}`.toLowerCase().includes(query.toLowerCase())) && (riskFilter === "All risk" || (riskFilter === "Critical" ? c.risk >= 70 : c.risk < 70)));
  const allVisibleSelected = filtered.length > 0 && filtered.every(c => selectedIds.has(c.id));
  const toggleAll = () => setSelectedIds(current => {
    const next = new Set(current);
    if (allVisibleSelected) filtered.forEach(c => next.delete(c.id));
    else filtered.forEach(c => next.add(c.id));
    return next;
  });
  const toggleCase = (caseId:string) => {
    const caseItem=cases.find(item=>item.id===caseId);
    if(caseItem) onSelectCase(caseItem);
    setSelectedIds(new Set([caseId]));
  };
  return <div className="page-content">
    <div className="mission-banner"><div><Brand/><span className="mission-divider"/><div><p>BUILD TO CARE</p><strong>Protecting every healthcare dollar with explainable intelligence.</strong></div></div><Badge tone="success">ENGINE ACTIVE v3.5.0 · SUB-100MS COPILOT CONTEXT READY</Badge></div>
    <div className="page-intro"><div><p className="eyebrow">{new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" }).toUpperCase()}</p><h2>Investigation overview</h2><p className="muted">Prioritized FWA intelligence across 1.8M adjudicated claims.</p></div><div className="intro-actions"><Button icon="refresh">Refresh data</Button><Button variant="primary" icon="plus" onClick={() => openAction("Refer to SIU")}>Create investigation</Button></div></div>
    <div className="kpi-grid">
      <Kpi label="Total Claims Analyzed" value="1.84M" trend="+12.4%" tone="blue" icon="scan"/>
      <Kpi label="Flagged High Risk" value="1,284" trend="+8.1%" tone="red" icon="shield"/>
      <Kpi label="Projected 90-Day Loss" value="$8.42M" trend="-$640K" tone="amber" icon="clock"/>
      <Kpi label="Active Fraud Rings" value="17" trend="+3 new" tone="purple" icon="network"/>
    </div>
    <Card className="queue-card">
      <div className="card-head"><div><h3>Priority investigation queue</h3><p>Cases ranked by composite risk and financial exposure.</p></div><div className="updated"><span className="pulse"/> Live · updated 42s ago</div></div>
      <div className="toolbar">
        <label className="search-input"><Icon name="search"/><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search Case ID, provider, NPI…"/></label>
        <select value={riskFilter} onChange={e => setRiskFilter(e.target.value)}><option>All risk</option><option>Critical</option><option>Moderate / Low</option></select>
        <select><option>All statuses</option><option>Under Review</option><option>Escalated</option></select>
        <Button icon="filter">More filters <span className="count">2</span></Button>
        <Button icon="refresh">Refresh</Button>
      </div>
      <div className="table-wrap"><table><thead><tr><th><input type="checkbox" aria-label="Select all visible investigations" checked={allVisibleSelected} onChange={toggleAll}/></th><th>Case ID / Investigation</th><th>Provider / NPI</th><th>Total Billed</th><th>Composite Risk</th><th>Primary Flag</th><th>Status</th><th>Last Updated</th><th aria-label="Actions"/></tr></thead>
        <tbody>{filtered.map(c => <tr key={c.id} className={selectedCase.id === c.id ? "selected" : ""} onClick={() => onSelectCase(c)} onDoubleClick={()=>openCase(c)}>
          <td><input type="checkbox" aria-label={`Select ${c.id}`} checked={selectedIds.has(c.id)} onClick={event=>event.stopPropagation()} onChange={() => toggleCase(c.id)}/></td>
          <td><button className="case-link" onClick={event=>{event.stopPropagation();openCase(c)}}>{c.id}</button><small>{c.title}</small></td>
          <td><b>{c.provider}</b><small>NPI {c.npi}</small></td><td><b>{c.billed}</b></td>
          <td><RiskBadge risk={c.risk}/></td><td>{c.flag}</td><td><Badge tone={c.status === "Escalated" ? "critical" : c.status === "Triage" ? "neutral" : "info"}>{c.status}</Badge></td><td>{c.updated}</td>
          <td><button className="icon-button"><Icon name="more"/></button></td>
        </tr>)}</tbody></table></div>
      {filtered.length === 0 && <div className="empty-state"><Icon name="search" size={28}/><h3>No investigations found</h3><p>Try adjusting your search or risk filters.</p><Button onClick={() => { setQuery(""); setRiskFilter("All risk"); }}>Clear filters</Button></div>}
      <div className="table-footer"><span>{filtered.length?`Showing all ${filtered.length} investigations`:"No investigations to show"}</span></div>
    </Card>
  </div>;
}

type TriggeredRule=[string,"critical"|"warning",string];

function getTriggeredRules(caseItem:QueueCase):TriggeredRule[] {
  const ruleMap:Record<string,TriggeredRule[]>={
    "CASE-001":[["UPCODING","critical","HIGH"],["IMPOSSIBLE GEOGRAPHY","warning","MEDIUM"],["DUPLICATE BILLING","critical","HIGH"]],
    "CASE-002":[["CPT UPCODING","critical","HIGH"],["DOCUMENTATION MISMATCH","warning","MEDIUM"]],
    "CASE-004":[["DUPLICATE BILLING","critical","HIGH"],["REPEAT SUBMISSION","warning","MEDIUM"]],
    "CASE-005":[["IMPOSSIBLE GEOGRAPHY","critical","HIGH"],["OVERLAPPING SERVICES","warning","MEDIUM"]],
    "CASE-006":[["PROCEDURE UNBUNDLING","warning","MEDIUM"]],
    "CASE-007":[["REFERRAL CONCENTRATION","critical","HIGH"],["NETWORK COLLUSION","critical","HIGH"]],
    "CASE-008":[["MODIFIER MISUSE","warning","MEDIUM"]],
    "CASE-009":[["PHANTOM BILLING","critical","HIGH"],["BENEFICIARY MISMATCH","critical","HIGH"]],
    "CASE-010":[["EXCESSIVE FREQUENCY","warning","MEDIUM"]],
    "CASE-011":[["PROVIDER IDENTITY MISMATCH","warning","MEDIUM"]],
    "CASE-012":[["DME NETWORK PATTERN","critical","HIGH"],["DUPLICATE EQUIPMENT","warning","MEDIUM"]],
  };
  return ruleMap[caseItem.id]??(caseItem.risk<40?[]:[[caseItem.flag.toUpperCase(),caseItem.risk>=70?"critical":"warning",caseItem.risk>=70?"HIGH":"MEDIUM"]]);
}

function EvidencePanel({caseItem}:{caseItem:QueueCase}) {
  const tier=caseItem.risk>=70?"CRITICAL":caseItem.risk>=40?"MODERATE":"LOW";
  const deviation=caseItem.risk>=70?"Very high deviation":caseItem.risk>=40?"Moderate deviation":"Low deviation";
  const gaugeTone=caseItem.risk>=70?"critical":caseItem.risk>=40?"moderate":"low";
  const triggeredRules=getTriggeredRules(caseItem);
  const items = [["Case ID",caseItem.id],["Provider",caseItem.provider],["NPI",caseItem.npi],["Claim amount",caseItem.billed],["Risk tier",tier],["Composite risk",`${caseItem.risk} / 100`],["Primary finding",caseItem.flag],["Case status",caseItem.status]];
  return <div className="evidence-panel">
    <div className="section-head"><div><p className="eyebrow">EXPLAINABLE EVIDENCE</p><h3>Evidence matrix</h3></div><RiskBadge risk={caseItem.risk}/></div>
    <div className="evidence-list">{items.map(([k,v]) => <div key={k}><span>{k}</span><b>{v}</b></div>)}</div>
    <div className={`gauge-wrap gauge-${gaugeTone}`}><div className="gauge" style={{"--score": `${caseItem.risk}%`} as React.CSSProperties}><div><strong>{caseItem.risk}%</strong><span>ML ANOMALY</span></div></div><p>{deviation}</p><small>Peer cohort analysis for {caseItem.provider}</small></div>
    <div className="rules"><p className="eyebrow">RULES TRIGGERED · {triggeredRules.length}</p>
      {triggeredRules.map(rule=><div key={rule[0]}><span>{rule[0]}</span><Badge tone={rule[1]}>{rule[2]}</Badge></div>)}
      {triggeredRules.length===0&&<div className="rules-clear"><Icon name="check"/><span><b>No material rules triggered</b><small>Claim activity is within expected policy thresholds.</small></span></div>}
    </div>
  </div>;
}

function PolicyPanel({caseItem}:{caseItem:QueueCase}) {
  const [expanded, setExpanded] = useState(0);
  const finding=`${caseItem.flag} ${caseItem.title}`.toLowerCase();
  const policyGroups:{match:boolean;policies:Array<{id:string;title:string;text:string;evidence:string;cite:string}>}[] = [
    {match:finding.includes("upcod"),policies:[
      {id:"CMS-NCCI-2024 §9.3",title:"Evaluation & Management Coding",text:"Higher-level E/M codes require documentation supporting the reported complexity or total encounter time.",evidence:`Claims associated with ${caseItem.provider} contain coding patterns above the expected peer level.`,cite:"NCCI Policy Manual, Ch. XI, §30.6.1"},
      {id:"CMS-PUB-100-04 §12",title:"Documentation Requirements",text:"The medical record must support the level of service reported on the claim.",evidence:"Submitted service levels require focused documentation validation before payment.",cite:"Medicare Claims Processing Manual, Ch. 12"},
    ]},
    {match:finding.includes("geograph")||finding.includes("overlapping"),policies:[
      {id:"AHC-FWA-117 §4.2",title:"Geographic Service Integrity",text:"Concurrent services at geographically incompatible locations require pre-payment review.",evidence:`Service activity for ${caseItem.provider} indicates locations or times that cannot reasonably overlap.`,cite:"A Health Payment Integrity Policy §4.2"},
      {id:"CMS-PIM §4.18",title:"Overlapping Service Validation",text:"Claims with conflicting service times or locations must be validated against source records.",evidence:"Related encounters require timestamp, rendering-provider, and location verification.",cite:"Medicare Program Integrity Manual, Ch. 4 §4.18"},
    ]},
    {match:finding.includes("duplicate")||finding.includes("repeat submission"),policies:[
      {id:"CMS-1500 §24D",title:"Duplicate Service Submission",text:"Identical services must not be rebilled for the same beneficiary and service date.",evidence:`Repeated claim attributes were identified within the ${caseItem.billed} case exposure.`,cite:"Medicare Claims Processing Manual, Ch. 1"},
      {id:"AH-FWA-204",title:"Repeat Claim-Line Controls",text:"Duplicate procedure, member, provider, and service-date combinations require denial or manual review.",evidence:"Matching service lines require source-document comparison.",cite:"A Health Claims Integrity Standard §7.1"},
    ]},
    {match:finding.includes("unbundl"),policies:[
      {id:"CMS-NCCI-2024 §1.2",title:"Procedure-to-Procedure Edits",text:"Services included in a comprehensive procedure must not be billed separately without a supported modifier.",evidence:`Procedure combinations billed by ${caseItem.provider} require NCCI edit validation.`,cite:"National Correct Coding Initiative Policy Manual, Ch. 1"},
    ]},
    {match:finding.includes("modifier"),policies:[
      {id:"CMS-NCCI-2024 §1.4",title:"Modifier Integrity",text:"Modifiers may bypass an edit only when the clinical record supports a distinct service.",evidence:"The reported modifier pattern requires documentation of separate encounters or anatomical sites.",cite:"NCCI Policy Manual, Ch. 1 §1.4"},
    ]},
    {match:finding.includes("referral")||finding.includes("network")||finding.includes("collusion"),policies:[
      {id:"42 CFR §1001.952",title:"Referral Relationship Integrity",text:"Financial and referral relationships must not induce or reward federally reimbursable services.",evidence:`Dense referral activity involving ${caseItem.provider} exceeds the expected network baseline.`,cite:"Federal Anti-Kickback Statute Safe Harbors"},
      {id:"AH-FWA-311",title:"Coordinated Network Review",text:"Concentrated reciprocal referrals require entity-link and ownership review.",evidence:"Connected entities show repeated referral and billing relationships.",cite:"A Health Network Integrity Standard §3.6"},
    ]},
    {match:finding.includes("phantom"),policies:[
      {id:"31 USC §3729",title:"False Claims Submission",text:"Claims may not be submitted for services that were not rendered as represented.",evidence:`Service existence and beneficiary receipt require validation for ${caseItem.provider}.`,cite:"False Claims Act, 31 USC §3729"},
      {id:"CMS-PIM §3.2.3",title:"Beneficiary Verification",text:"High-risk services should be confirmed through records and beneficiary contact.",evidence:"Claim samples require proof of delivery or encounter documentation.",cite:"Medicare Program Integrity Manual, Ch. 3"},
    ]},
    {match:finding.includes("frequency")||finding.includes("velocity"),policies:[
      {id:"CMS-PIM §3.3.2",title:"Medical Necessity and Utilization",text:"Service frequency must be reasonable, necessary, and supported by the clinical record.",evidence:`Billing velocity for ${caseItem.provider} differs from the relevant provider cohort.`,cite:"Medicare Program Integrity Manual, Ch. 3"},
    ]},
    {match:finding.includes("identity"),policies:[
      {id:"42 CFR §424.516",title:"Provider Enrollment Accuracy",text:"Enrollment, ownership, and practice information must remain complete and accurate.",evidence:"Provider identity attributes require reconciliation before adverse action.",cite:"Medicare Provider Enrollment Requirements"},
    ]},
    {match:finding.includes("dme"),policies:[
      {id:"CMS-PIM §5.2",title:"DMEPOS Supplier Integrity",text:"DMEPOS claims require valid orders, delivery records, and enrolled supplier information.",evidence:`Equipment billing associated with ${caseItem.provider} shows coordinated network indicators.`,cite:"Medicare Program Integrity Manual, Ch. 5"},
      {id:"AH-FWA-422",title:"Durable Equipment Network Review",text:"Shared beneficiaries, ordering providers, and suppliers require coordinated review.",evidence:"Entity relationships indicate concentrated equipment ordering and fulfillment.",cite:"A Health DME Integrity Standard §4.2"},
    ]},
  ];
  const policies=caseItem.risk<40?[]:(policyGroups.find(group=>group.match)?.policies??[
    {id:"AH-FWA-100",title:"Payment Integrity Review",text:"Claims with material anomaly indicators require evidence-based pre-payment review.",evidence:`${caseItem.flag} was identified for ${caseItem.provider} at ${caseItem.risk}% composite risk.`,cite:"A Health Payment Integrity Standard §2.1"},
  ]);
  const synchronizedDate=new Intl.DateTimeFormat("en-US",{month:"short",day:"numeric",year:"numeric"}).format(new Date());
  useEffect(()=>setExpanded(policies.length?0:-1),[caseItem.id]);
  return <Card className="policy-panel"><div className="policy-head"><div className="policy-icon"><Icon name="shield"/></div><div><p className="eyebrow">POLICY RAG INSPECTOR</p><h3>Regulatory evidence</h3><p>Grounded citations from approved policy corpus.</p></div><Badge tone={policies.length?"purple":"success"}>{policies.length} {policies.length===1?"MATCH":"MATCHES"}</Badge></div>
    <div className="policy-cards">{policies.map((p,i) => <button key={p.id} className={`policy-card ${expanded === i ? "expanded" : ""}`} onClick={() => setExpanded(expanded === i ? -1 : i)}>
      <span className="policy-card-title"><span><small>{p.id}</small><b>{p.title}</b></span><Icon name="chevron"/></span>
      {expanded === i && <span className="policy-body"><span><label>RELEVANT SECTION</label>{p.text}</span><span className="violation"><label>VIOLATION EVIDENCE</label>{p.evidence}</span><span className="citation">Citation: {p.cite}</span></span>}
    </button>)}{policies.length===0&&<div className="policy-empty"><Icon name="check"/><div><b>No material policy conflicts found</b><p>This case is currently within validated policy thresholds. Continue routine monitoring.</p></div></div>}</div>
    <div className="grounded"><Icon name="check"/> Evidence retrieved from validated policy index · Last synchronized {synchronizedDate}</div>
  </Card>;
}

function NetworkGraph({ caseItem }: { caseItem: QueueCase }) {
  const [node, setNode] = useState("Dr. Alex Mercer");
  const [remoteEntities, setRemoteEntities] = useState<number | null>(null);
  useEffect(() => {
    api.graph(caseItem.id).then(payload => {
      const nodes = payload.nodes ?? (payload.graph as Record<string, unknown> | undefined)?.nodes;
      if (Array.isArray(nodes)) setRemoteEntities(nodes.length);
    }).catch(() => undefined);
  }, [caseItem.id]);
  const nodes = [
    {x:270,y:185,r:46,label:"Dr. Alex Mercer",type:"PROVIDER",risk:"87",cls:"provider"},
    {x:88,y:72,r:33,label:"Patient P-1872",type:"PATIENT",risk:"",cls:"patient"},
    {x:490,y:68,r:38,label:"Apex Diagnostic",type:"LAB",risk:"76",cls:"lab"},
    {x:520,y:280,r:38,label:"Mercer Clinic",type:"FACILITY",risk:"69",cls:"facility"},
    {x:102,y:316,r:34,label:"Dr. L. Shaw",type:"REFERRER",risk:"58",cls:"referrer"},
    {x:285,y:365,r:42,label:"Ring East 01",type:"FRAUD RING",risk:"92",cls:"ring"},
  ];
  return <Card className="network-card"><div className="card-head"><div><p className="eyebrow">ENTITY LINK ANALYSIS</p><h3>Fraud network</h3><p>{remoteEntities ?? 18} entities · 32 relationships · 7 suspicious links</p></div><div className="graph-tools"><button>−</button><button>+</button><button>Fit</button><button><Icon name="refresh" size={15}/></button></div></div>
    <div className="graph-layout"><svg className="network-svg" viewBox="0 0 600 430">
      <defs><marker id="arrow-red" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0 10 5 0 10z" fill="#ef4444"/></marker></defs>
      <path className="edge suspicious" d="M240 165 115 91M310 159 456 92M311 210 485 268M246 218 126 292M275 231 283 320" markerEnd="url(#arrow-red)"/>
      <path className="edge" d="M121 84 Q300 0 462 74M131 316 Q300 425 492 294"/>
      {nodes.map(n => <g key={n.label} className={`node ${n.cls} ${node===n.label?"node-selected":""}`} onClick={() => setNode(n.label)} role="button" tabIndex={0}>
        <circle cx={n.x} cy={n.y} r={n.r}/><circle className="node-ring" cx={n.x} cy={n.y} r={n.r+5}/><text className="node-type" x={n.x} y={n.y-5}>{n.type}</text><text className="node-label" x={n.x} y={n.y+10}>{n.label}</text>{n.risk && <text className="node-risk" x={n.x} y={n.y+25}>RISK {n.risk}%</text>}
      </g>)}
    </svg><div className="node-detail"><div className="node-detail-head"><span className="entity-icon"><Icon name="provider"/></span><div><small>SELECTED ENTITY</small><h4>{node}</h4></div></div><RiskBadge risk={node.includes("Ring") ? 92 : 87}/><dl><dt>NPI</dt><dd>1029384</dd><dt>Total billed</dt><dd>$2.48M</dd><dt>Connections</dt><dd>12 direct · 31 indirect</dd><dt>Community</dt><dd>Ring East Coast 01</dd></dl><div className="alert-box"><Icon name="network"/><span><b>Suspicious clustering</b>Entity is 4.8× more connected than cohort baseline.</span></div><Button variant="primary" className="full">Open entity profile</Button></div></div>
    <div className="graph-legend"><span><i className="legend-provider"/>Provider</span><span><i className="legend-patient"/>Patient</span><span><i className="legend-lab"/>Laboratory</span><span><i className="legend-ring"/>Fraud ring</span><span><i className="legend-edge"/>Suspicious relationship</span></div>
  </Card>;
}

function Forecast({ caseItem }: { caseItem: QueueCase }) {
  const [range, setRange] = useState("90D");
  return <div className="forecast-grid"><div className="mini-kpis">
    {[["Daily Billing Velocity","$18,420","+38% vs peer"],["30-Day Exposure","$552,600","Projected"],["60-Day Exposure","$1.08M","Projected"],["90-Day Exposure","$1.64M","Projected"]].map((a,i)=><Card key={a[0]}><span>{a[0]}</span><strong>{a[1]}</strong><small className={i===0?"danger-text":""}>{a[2]}</small></Card>)}
  </div><Card className="chart-card"><div className="card-head"><div><p className="eyebrow">FINANCIAL FORECAST</p><h3>Provider financial exposure</h3><p>Actual paid amount versus risk-adjusted projected exposure.</p></div><div className="range-tabs">{["30D","60D","90D"].map(r=><button className={range===r?"active":""} onClick={()=>setRange(r)} key={r}>{r}</button>)}</div></div>
  <div className="chart-legend"><span><i className="actual"/>Actual paid</span><span><i className="projected"/>Projected exposure</span><Badge tone="warning">CONFIDENCE 89%</Badge></div>
  <svg className="area-chart" viewBox="0 0 900 290" preserveAspectRatio="none"><defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#22c55e" stopOpacity=".3"/><stop offset="1" stopColor="#22c55e" stopOpacity="0"/></linearGradient></defs>
    {[40,100,160,220,280].map(y=><line key={y} x1="50" x2="880" y1={y} y2={y} className="grid-line"/>)}
    <path className="chart-area" d="M50 255 C130 240 180 235 250 210 S370 190 430 168 S540 135 600 112 S720 83 880 32 L880 280 L50 280Z"/>
    <path className="actual-line" d="M50 255 C130 240 180 235 250 210 S370 190 430 168"/><path className="projected-line" d="M430 168 C500 150 540 135 600 112 S720 83 880 32"/><line x1="430" x2="430" y1="25" y2="280" className="today-line"/>
    <circle cx="600" cy="112" r="5" className="chart-point"/><g className="chart-tooltip"><rect x="535" y="45" width="132" height="48" rx="4"/><text x="550" y="65">60-DAY EXPOSURE</text><text x="550" y="83">$1.08M</text></g>
    <text x="50" y="289">Current</text><text x="310" y="289">30 days</text><text x="575" y="289">60 days</text><text x="830" y="289">90 days</text>
  </svg></Card><FinancialForecastView providerNpi={caseItem.npi}/></div>;
}

function CaseWorkspace({ setPage, openAction, onCopilot, caseItem }: { setPage: (p: Page) => void; openAction: (a: string) => void; onCopilot: () => void; caseItem:QueueCase }) {
  const [tab, setTab] = useState("Investigation");
  const [showAllClaims,setShowAllClaims]=useState(false);
  const triggeredRules=getTriggeredRules(caseItem);
  const linkedClaimCount=caseItem.risk<40?6:48;
  const claimCount=showAllClaims?linkedClaimCount:Math.min(3,linkedClaimCount);
  const codeForRule=(rule:string)=>{
    if(rule.includes("UPCOD")) return "99215";
    if(rule.includes("GEOGRAPH")||rule.includes("OVERLAP")) return "99214";
    if(rule.includes("DUPLICATE")||rule.includes("REPEAT")) return "80053";
    if(rule.includes("DME")) return "E1390";
    if(rule.includes("MODIFIER")) return "97110-59";
    return "99213";
  };
  const visibleClaims=Array.from({length:claimCount},(_,index)=>{
    const rule=triggeredRules.length?triggeredRules[index%triggeredRules.length]:null;
    const date=new Date();
    date.setDate(date.getDate()-(index%14));
    return {
      id:`CLM-${caseItem.npi.slice(-3)}${String(201+index).padStart(3,"0")}`,
      service:new Intl.DateTimeFormat("en-US",{month:"short",day:"2-digit"}).format(date),
      code:codeForRule(rule?.[0]??""),
      amount:new Intl.NumberFormat("en-US",{style:"currency",currency:"USD",maximumFractionDigits:0}).format(185+((caseItem.risk*53+index*317)%5800)),
      finding:rule?.[0]??"NO MATERIAL FINDING",
      tone:rule?.[1]??"success" as "critical"|"warning"|"success",
    };
  });
  useEffect(()=>setShowAllClaims(false),[caseItem.id]);
  return <div className="page-content">
    <div className="case-header"><div><button className="back-link" onClick={()=>setPage("command")}>← Investigation queue</button><div className="case-title-row"><h2>{caseItem.id}</h2><RiskBadge risk={caseItem.risk}/><Badge tone="info">{caseItem.status.toUpperCase()}</Badge></div><p>{caseItem.title} · {caseItem.provider} · NPI {caseItem.npi}</p></div><div className="case-actions"><Button onClick={onCopilot} icon="spark">Ask Copilot</Button><Button onClick={()=>openAction("Request Medical Records")}>Request records</Button><Button variant="danger" onClick={()=>openAction("Pause Payment")}>Pause payment</Button><button className="icon-button"><Icon name="more"/></button></div></div>
    <div className="tabs">{["Investigation","Fraud Network","Policy Evidence","Financial Forecast"].map(t=><button className={tab===t?"active":""} onClick={()=>setTab(t)} key={t}>{t}{t==="Policy Evidence"&&<span>3</span>}</button>)}</div>
    {tab === "Investigation" && <div className="investigation-grid"><Card><EvidencePanel caseItem={caseItem}/><CaseWorkspaceView caseId={caseItem.id}/></Card><div className="center-stack"><PolicyPanel caseItem={caseItem}/><Card className="claims-card"><div className="card-head"><div><p className="eyebrow">LINKED CLAIMS</p><h3>Claims under review</h3></div><Button variant="ghost" onClick={()=>setShowAllClaims(!showAllClaims)}>{showAllClaims?"Show recent":`View all ${linkedClaimCount}`}</Button></div><table><thead><tr><th>Claim</th><th>Service</th><th>CPT</th><th>Amount</th><th>Finding</th></tr></thead><tbody>{visibleClaims.map(claim=><tr key={claim.id}><td>{claim.id}</td><td>{claim.service}</td><td>{claim.code}</td><td>{claim.amount}</td><td><Badge tone={claim.tone}>{claim.finding}</Badge></td></tr>)}</tbody></table>{showAllClaims&&<div className="claims-expanded-note"><Icon name="check"/> Showing all {linkedClaimCount} linked claims for {caseItem.id}</div>}</Card></div></div>}
    {tab === "Fraud Network" && <NetworkGraph caseItem={caseItem}/>}
    {tab === "Policy Evidence" && <div className="policy-page"><PolicyPanel caseItem={caseItem}/><Card className="policy-summary"><p className="eyebrow">EVIDENCE SUMMARY</p><h3>Policy compliance assessment</h3><div className="score-ring">{caseItem.risk}<span>/100</span></div><p>{caseItem.risk<40?"No material policy violation is currently supported. Continue routine monitoring.":"Case-specific evidence supports a potential policy violation. Human review is required before adverse action."}</p><Button variant="primary" onClick={onCopilot} icon="spark">Explain with Copilot</Button></Card></div>}
    {tab === "Financial Forecast" && <Forecast caseItem={caseItem}/>}
    <div className="sticky-actions"><span><Icon name="shield"/><span><b>Investigator decision</b><small>All actions create an immutable audit event.</small></span></span><div><Button onClick={()=>openAction("Mark False Positive")}>False positive</Button><Button onClick={()=>openAction("Approve")}>Approve</Button><Button variant="primary" onClick={()=>openAction("Refer to SIU")}>Refer to SIU</Button></div></div>
  </div>;
}

function ProviderPage({ setPage, caseItem }: { setPage:(p:Page)=>void; caseItem:QueueCase }) {
  const [monitoredProviders,setMonitoredProviders]=useState<Set<string>>(new Set());
  const [monitorNotice,setMonitorNotice]=useState("");
  const monitored=monitoredProviders.has(caseItem.npi);
  const initials=caseItem.provider.split(/\s+/).filter(Boolean).slice(0,2).map(word=>word[0]).join("").toUpperCase();
  const rules=getTriggeredRules(caseItem);
  const billedAmount=Number(caseItem.billed.replace(/[^0-9.]/g,""))||0;
  const claimCount=Math.max(42,Math.round(caseItem.risk*38+620));
  const averageClaim=Math.round(billedAmount/claimCount);
  const forecastAmount=billedAmount*(1.35+caseItem.risk/100);
  const money=(value:number)=>new Intl.NumberFormat("en-US",{style:"currency",currency:"USD",maximumFractionDigits:0}).format(value);
  const toggleMonitoring=()=>{
    const next=!monitored;
    setMonitoredProviders(current=>{const updated=new Set(current);if(next)updated.add(caseItem.npi);else updated.delete(caseItem.npi);return updated});
    setMonitorNotice(next?"Provider monitoring enabled. You will receive alerts for risk, billing velocity, and network changes.":"Provider monitoring stopped. Existing case alerts remain available in the audit trail.");
    window.setTimeout(()=>setMonitorNotice(""),4500);
  };
  return <div className="page-content"><div className="provider-hero"><div className="provider-avatar">{initials}</div><div><p className="eyebrow">PROVIDER INTELLIGENCE PROFILE</p><div className="case-title-row"><h2>{caseItem.provider}</h2><RiskBadge risk={caseItem.risk}/>{monitored&&<Badge tone="success">MONITORING</Badge>}</div><p>NPI {caseItem.npi} · Provider under review · {caseItem.flag}</p></div><div className="provider-actions"><Button variant={monitored?"primary":"secondary"} icon={monitored?"check":"bell"} onClick={toggleMonitoring}>{monitored?"Monitoring active":"Monitor provider"}</Button><Button variant="primary" onClick={()=>setPage("case")}>Open {caseItem.id}</Button></div></div>
  {monitorNotice&&<div className={`monitor-notice ${monitored?"active":""}`}><Icon name={monitored?"bell":"x"}/><span><b>{monitored?"Continuous monitoring active":"Monitoring disabled"}</b>{monitorNotice}</span><button onClick={()=>setMonitorNotice("")}><Icon name="x" size={14}/></button></div>}
  <div className="provider-kpis">{[["Total Claims",claimCount.toLocaleString(),"12 months"],["Case Exposure",caseItem.billed,caseItem.id],["Average Claim",money(averageClaim),"Calculated"],["Risk Score",`${caseItem.risk} / 100`,caseItem.risk>=70?"Critical":caseItem.risk>=40?"Moderate":"Low"],["Billing Velocity",`${Math.max(2,Number((caseItem.risk/5).toFixed(1)))} / day`,"Risk adjusted"],["Fraud Indicators",`${rules.length} active`,caseItem.flag]].map((x,i)=><Card key={x[0]}><span>{x[0]}</span><strong>{x[1]}</strong><small className={i>2&&caseItem.risk>=70?"danger-text":""}>{x[2]}</small></Card>)}</div>
  <div className="provider-grid"><Card><div className="card-head"><div><p className="eyebrow">BEHAVIORAL PATTERNS</p><h3>Detected billing behaviors</h3></div><Badge tone={rules.length?"critical":"success"}>{rules.length} ACTIVE</Badge></div>
    {rules.map((rule,index)=><div className="behavior" key={rule[0]}><div><span className="behavior-icon"><Icon name="scan"/></span><span><b>{rule[0]}</b><small>Linked to {caseItem.id} · {rule[2].toLowerCase()} severity</small></span></div><div className="risk-bar"><i style={{width:`${Math.max(25,caseItem.risk-index*9)}%`}}/><span>{Math.max(25,caseItem.risk-index*9)}%</span></div></div>)}{rules.length===0&&<div className="empty-state"><Icon name="check"/><h3>No active behavioral findings</h3><p>This provider is currently within expected peer thresholds.</p></div>}
  </Card><Card><div className="card-head"><div><p className="eyebrow">FINANCIAL OUTLOOK</p><h3>90-day exposure</h3></div><button className="text-button" onClick={()=>setPage("case")}>Open forecast →</button></div><div className="forecast-total"><strong>{money(forecastAmount)}</strong><Badge tone="warning">{Math.min(96,caseItem.risk+7)}% CONFIDENCE</Badge></div><svg className="spark-chart" viewBox="0 0 500 130"><path d="M5 120 C60 112 85 100 125 98 S180 75 230 80 S300 52 350 54 S420 25 495 10"/><path className="fill" d="M5 120 C60 112 85 100 125 98 S180 75 230 80 S300 52 350 54 S420 25 495 10 L495 130 L5 130Z"/></svg></Card></div>
  <Card className="history-card"><div className="card-head"><div><p className="eyebrow">HISTORICAL SIU DECISIONS</p><h3>Prior investigations</h3></div><Button variant="ghost" onClick={()=>setPage("audit")}>View audit trail</Button></div><table><thead><tr><th>Date</th><th>Issue</th><th>Action</th><th>AI Confidence</th><th>Investigator</th></tr></thead><tbody><tr><td>Aug 18, 2026</td><td>Duplicate outpatient services</td><td><Badge tone="warning">PAUSE_PAYMENT</Badge></td><td>92%</td><td>M. Chen</td></tr><tr><td>Mar 02, 2026</td><td>Elevated E/M codes</td><td><Badge tone="info">FLAG_FOR_SIU</Badge></td><td>84%</td><td>J. Lewis</td></tr><tr><td>Nov 14, 2025</td><td>Billing velocity spike</td><td><Badge tone="success">CLEARED</Badge></td><td>71%</td><td>A. Patel</td></tr></tbody></table></Card></div>;
}

function ClaimAnalyzer({caseItem}:{caseItem:QueueCase}) {
  type ClaimForm={provider:string;patient:string;cpt:string;amount:string;serviceDate:string;location:string;diagnosisCode:string;facility:string;metadata:string;notes:string};
  const emptyForm=(item:QueueCase):ClaimForm=>({provider:`${item.provider} · NPI ${item.npi}`,patient:"",cpt:"",amount:"",serviceDate:"",location:"",diagnosisCode:"",facility:"",metadata:"",notes:""});
  const [scenario,setScenario]=useState("custom");
  const [form,setForm]=useState<ClaimForm>(()=>emptyForm(caseItem));
  const [result,setResult]=useState(false);
  const [loading,setLoading]=useState(false);
  const [analysisError,setAnalysisError]=useState("");
  useEffect(()=>{setForm(emptyForm(caseItem));setScenario("custom");setResult(false);setAnalysisError("")},[caseItem.id]);
  const update=(field:keyof ClaimForm,value:string)=>{setForm(current=>({...current,[field]:value}));setScenario("custom");setResult(false);setAnalysisError("")};
  const loadScenario=(next:string)=>{
    const today=new Date().toISOString().slice(0,10);
    const scenarios:Record<string,Partial<ClaimForm>>={
      upcoding:{patient:"Patient P-1872",cpt:"99215",amount:"4860.00",serviceDate:today,location:"New York, NY",diagnosisCode:"R05",facility:`${caseItem.provider} Practice`,metadata:"POS 11 · Modifier 25",notes:"Established patient office visit. 22 minutes documented. Moderate-complexity decision-making."},
      geography:{patient:"Patient P-2048",cpt:"99214",amount:"3725.00",serviceDate:today,location:"Boston, MA",diagnosisCode:"R05",facility:"Remote service location",metadata:"POS 11 · Concurrent encounter",notes:"A second service was recorded in New York within the same two-hour period."},
      duplicate:{patient:"Patient P-3194",cpt:"80053",amount:"2420.00",serviceDate:today,location:"New York, NY",diagnosisCode:"Z00",facility:`${caseItem.provider} Practice`,metadata:"Duplicate claim-line candidate",notes:"Same beneficiary, procedure, provider, and date of service as a previously submitted claim."},
      clean:{patient:"Patient P-4102",cpt:"99213",amount:"185.00",serviceDate:today,location:"New York, NY",diagnosisCode:"J00",facility:`${caseItem.provider} Practice`,metadata:"POS 11 · No modifier",notes:"Established patient visit with documentation supporting the reported service level."},
    };
    setForm(current=>({...current,...scenarios[next]}));setScenario(next);setResult(false);setAnalysisError("");
  };
  const requiredComplete=Boolean(form.provider&&form.patient&&form.cpt&&form.amount&&Number.isFinite(Number(form.amount))&&form.serviceDate&&form.location&&form.diagnosisCode);
  const resultRisk=scenario==="clean"?12:scenario==="custom"?caseItem.risk:Math.max(caseItem.risk,82);
  const finding=scenario==="clean"?"None":scenario==="upcoding"?"CPT 99215 upcoding":scenario==="duplicate"?"Duplicate billing":scenario==="geography"?"Impossible geography":caseItem.flag;
  const analyze=async()=>{setLoading(true);setResult(false);setAnalysisError("");try{await api.analyze({providerNpi:caseItem.npi,memberId:form.patient,cptCode:form.cpt,claimAmount:Number(form.amount),timestamp:`${form.serviceDate}T00:00:00Z`,location:form.location,diagnosisCode:form.diagnosisCode,facilityId:form.facility});}catch(error){setAnalysisError(error instanceof Error?error.message:"Live claim analysis is unavailable.");}finally{setLoading(false);setResult(true)}};
  return <div className="page-content analyzer-page"><div className="page-intro"><div><p className="eyebrow">REAL-TIME FWA DETECTION</p><h2>Claim Analyzer</h2><p className="muted">Analyze a new claim in the context of {caseItem.id} and {caseItem.provider}.</p></div><div className="analyzer-status"><Badge tone="info">{caseItem.id} LOADED</Badge><Badge tone="success">ENGINE READY · 42ms</Badge></div></div>
  <div className="demo-strip"><span>Load demo scenario</span>{["upcoding","geography","duplicate","clean"].map(s=><button className={scenario===s?"active":""} onClick={()=>loadScenario(s)} key={s}>Test {s==="geography"?"Impossible Geography":s[0].toUpperCase()+s.slice(1)}</button>)}</div>
  <div className="analyzer-grid"><Card className="claim-form"><div className="card-head"><div><p className="eyebrow">CLAIM INPUT</p><h3>Claim details</h3></div><small>Provider loaded from SIU case · Fields marked * are required</small></div>
    <div className="form-grid">
      <label><span>Provider *</span><input value={form.provider} readOnly/></label>
      <label><span>Patient *</span><input value={form.patient} onChange={e=>update("patient",e.target.value)} placeholder="Enter patient or beneficiary ID"/></label>
      <label><span>CPT / HCPCS *</span><input value={form.cpt} onChange={e=>update("cpt",e.target.value)} placeholder="Enter procedure code"/></label>
      <label><span>Claim amount *</span><input type="number" min="0" step="0.01" value={form.amount} onChange={e=>update("amount",e.target.value)} placeholder="Enter claim amount"/></label>
      <label><span>Service date *</span><input type="date" value={form.serviceDate} onChange={e=>update("serviceDate",e.target.value)}/></label>
      <label><span>Location *</span><input value={form.location} onChange={e=>update("location",e.target.value)} placeholder="City, state or service location"/></label>
      <label><span>Diagnosis code *</span><input value={form.diagnosisCode} onChange={e=>update("diagnosisCode",e.target.value)} placeholder="Enter ICD-10-CM code"/></label>
      <label><span>Facility</span><input value={form.facility} onChange={e=>update("facility",e.target.value)} placeholder="Enter facility name"/></label>
      <label><span>Claim metadata</span><input value={form.metadata} onChange={e=>update("metadata",e.target.value)} placeholder="Place of service, modifiers, units"/></label>
    </div>
    <label className="full-field"><span>Clinical / billing notes</span><textarea value={form.notes} onChange={e=>update("notes",e.target.value)} placeholder="Enter documentation or billing context for analysis"/></label>
    <Button variant="primary" icon="scan" onClick={analyze} loading={loading} disabled={!requiredComplete} className="analyze-button">ANALYZE CLAIM</Button>
  </Card><Card className={`analysis-result ${result?"has-result":""}`}>{!result && !loading && <div className="empty-state tall"><span className="scan-orb"><Icon name="scan" size={34}/></span><h3>Ready to analyze</h3><p>Complete the required claim fields or choose a demonstration scenario.</p></div>}{loading&&<div className="loading-state"><div className="scanner"/><h3>Analyzing claim evidence</h3><p>Running policy rules, anomaly model and {caseItem.id} graph context…</p><div className="skeleton-lines"><i/><i/><i/></div></div>}{result&&<><div className="result-head"><div><p className="eyebrow">{analysisError?"DEMO PREVIEW · API UNAVAILABLE":"LOCAL DEMO PREVIEW"}</p><h3>{resultRisk<40?"No material risk detected":"Potential risk detected"}</h3></div><RiskBadge risk={resultRisk}/></div>{analysisError&&<div className="error-note" role="alert">{analysisError}. Displaying the local scenario preview only.</div>}<div className="result-score"><div className="score-ring">{resultRisk}<span>/100</span></div><div><span>COMPOSITE RISK</span><b>{resultRisk>=70?"CRITICAL":resultRisk>=40?"MODERATE":"LOW"}</b><small>Case context: {caseItem.id}</small></div></div><div className="result-sections"><div><span>Primary flag</span><b>{finding}</b></div><div><span>Submitted claim</span><b>{form.cpt} · {new Intl.NumberFormat("en-US",{style:"currency",currency:"USD"}).format(Number(form.amount))}</b></div><div><span>Evidence</span><p>{resultRisk<40?"Claim aligns with the selected provider context and policy requirements.":`Claim evidence aligns with the ${finding.toLowerCase()} indicators already associated with ${caseItem.id}.`}</p></div></div><Button variant="primary" className="full">Create investigation case</Button></>}</Card></div></div>;
}

function SecondBrain({ setPage, caseItem, onCopilot }: { setPage:(p:Page)=>void; caseItem:QueueCase; onCopilot:()=>void }) {
  const [knowledgeTab,setKnowledgeTab]=useState("Provider Intelligence");
  const [searchOpen,setSearchOpen]=useState(false);
  const [knowledgeQuery,setKnowledgeQuery]=useState("");
  const rules=getTriggeredRules(caseItem);
  const initials=caseItem.provider.split(/\s+/).filter(Boolean).slice(0,2).map(word=>word[0]).join("").toUpperCase();
  const claimCount=caseItem.risk<40?6:48;
  const entityCount=Math.max(2,Math.round(caseItem.risk/7));
  const backlinkCount=rules.length*4+6;
  const synthesis=caseItem.risk<40
    ? `${caseItem.provider} is currently within expected peer and policy thresholds. ${caseItem.id} remains available for routine monitoring and human review.`
    : `${caseItem.provider} exhibits ${rules.length} active behavioral ${rules.length===1?"pattern":"patterns"} associated with ${caseItem.flag.toLowerCase()}. Current evidence connects ${claimCount} claims and ${entityCount} related entities to ${caseItem.id}.`;
  const backlinks=[`[[Case: ${caseItem.id}]]`,`[[Provider NPI: ${caseItem.npi}]]`,...rules.map(rule=>`[[Finding: ${rule[0]}]]`),`[[Status: ${caseItem.status}]]`];
  const knowledgeTabs=["Provider Intelligence","Network Entities","Policy Evidence","Related Claims","SIU Decisions"];
  const knowledgeEntries=[
    ...knowledgeTabs.map(tab=>({label:tab,detail:`Open ${tab.toLowerCase()}`,tab})),
    {label:caseItem.id,detail:caseItem.title,tab:"SIU Decisions"},
    {label:caseItem.provider,detail:`NPI ${caseItem.npi}`,tab:"Provider Intelligence"},
    ...rules.map(rule=>({label:rule[0],detail:`${rule[2]} severity finding`,tab:"Policy Evidence"})),
  ];
  const knowledgeResults=knowledgeEntries.filter(entry=>`${entry.label} ${entry.detail}`.toLowerCase().includes(knowledgeQuery.toLowerCase()));
  const references=[
    {label:caseItem.id,detail:"Active investigation",action:()=>setPage("case")},
    {label:caseItem.provider,detail:"Billing provider",action:()=>setPage("provider")},
    {label:`NPI ${caseItem.npi}`,detail:"Provider identity",action:()=>setPage("provider")},
    {label:caseItem.flag,detail:"Primary evidence",action:()=>setKnowledgeTab("Policy Evidence")},
  ];
  useEffect(()=>setKnowledgeTab("Provider Intelligence"),[caseItem.id]);
  return <div className="page-content brain-page"><div className="page-intro"><div><p className="eyebrow purple-text">DEEP-DIVE WORKSPACE</p><h2>Institutional Intelligence Hub</h2><p className="muted">Case-specific institutional memory across claims, policies, decisions, and connected entities.</p></div><div><Button icon="search" onClick={()=>setSearchOpen(true)}>Search knowledge</Button> <Button variant="primary" icon="spark" onClick={onCopilot}>Ask the workspace</Button></div></div>
  <div className="wiki-layout"><aside className="wiki-index"><label>KNOWLEDGE INDEX</label>{knowledgeTabs.map((x,i)=><button className={knowledgeTab===x?"active":""} onClick={()=>setKnowledgeTab(x)} key={x}><Icon name={i===0?"provider":i===1?"network":i===2?"shield":i===3?"case":"audit"}/>{x}<span>{[1,entityCount,Math.max(0,rules.length),claimCount,caseItem.status==="Triage"?0:1][i]}</span></button>)}</aside>
  <article className="wiki-document"><div className="wiki-title"><div className="wiki-provider">{initials}</div><div><p className="eyebrow">CASE-SPECIFIC PROVIDER INTELLIGENCE</p><h2>{caseItem.provider}</h2><p>NPI: {caseItem.npi} · {caseItem.id} · Last synthesized just now</p></div><RiskBadge risk={caseItem.risk}/></div>
  {knowledgeTab==="Provider Intelligence"&&<><div className="wiki-callout"><Icon name="spark"/><div><b>AI synthesis</b><p>{synthesis} <button>[[Primary finding: {caseItem.flag}]]</button>.</p></div></div><section className="wiki-section"><h3>Behavioral Patterns</h3>{rules.length?<ul>{rules.map(rule=><li key={rule[0]}><b>{rule[0]}</b> — {rule[2].toLowerCase()}-severity evidence associated with {caseItem.id}. See <button onClick={()=>setKnowledgeTab("Policy Evidence")}>[[Policy evidence: {rule[0]}]]</button></li>)}</ul>:<div className="wiki-clean"><Icon name="check"/><span><b>No active behavioral patterns</b><small>Current evidence remains within validated peer thresholds.</small></span></div>}</section><section className="wiki-section"><h3>Related Entities & Backlinks</h3><div className="backlinks">{backlinks.map(x=><button key={x}>{x}<Icon name="arrow" size={13}/></button>)}</div></section></>}
  {knowledgeTab==="Network Entities"&&<section className="wiki-section knowledge-view"><p className="eyebrow">ENTITY LINK ANALYSIS</p><h3>Connected network entities</h3><p className="knowledge-intro">{entityCount} entities are associated with {caseItem.id}. Connections remain investigative leads until independently verified.</p><div className="entity-list">{Array.from({length:Math.min(entityCount,8)},(_,index)=><div key={index}><span className="entity-icon"><Icon name={index%3===0?"provider":index%3===1?"case":"network"}/></span><span><b>{index===0?caseItem.provider:index%3===1?`Beneficiary P-${1872+index}`:`Related entity ${String(index+1).padStart(2,"0")}`}</b><small>{index===0?`NPI ${caseItem.npi}`:`${index+1} direct claim relationships`}</small></span><Badge tone={index===0?"critical":"warning"}>{index===0?"PRIMARY":"LINKED"}</Badge></div>)}</div></section>}
  {knowledgeTab==="Policy Evidence"&&<section className="wiki-section knowledge-view"><p className="eyebrow">GROUNDED POLICY CONTEXT</p><h3>Policy evidence for {caseItem.id}</h3><p className="knowledge-intro">Findings are mapped to the validated policy index and require human interpretation.</p>{rules.length?<div className="knowledge-policy-list">{rules.map(rule=><div key={rule[0]}><Icon name="shield"/><span><b>{rule[0]}</b><small>{rule[2]}-severity finding · Policy citation available in Case Investigation</small></span><Badge tone={rule[1]}>{rule[2]}</Badge></div>)}</div>:<div className="wiki-clean"><Icon name="check"/><span><b>No policy conflicts found</b><small>This provider is currently within validated policy thresholds.</small></span></div>}<Button variant="primary" onClick={()=>setPage("case")}>Open full policy evidence</Button></section>}
  {knowledgeTab==="Related Claims"&&<section className="wiki-section knowledge-view"><p className="eyebrow">CLAIM RELATIONSHIPS</p><h3>{claimCount} claims linked to {caseItem.id}</h3><p className="knowledge-intro">A representative set of claim lines connected to the selected provider and current findings.</p><div className="knowledge-claims"><table><thead><tr><th>Claim</th><th>Provider NPI</th><th>Finding</th><th>Risk</th></tr></thead><tbody>{Array.from({length:Math.min(claimCount,10)},(_,index)=>{const rule=rules[index%Math.max(1,rules.length)];return <tr key={index}><td>CLM-{caseItem.npi.slice(-3)}{String(201+index)}</td><td>{caseItem.npi}</td><td>{rule?.[0]??"No material finding"}</td><td><RiskBadge risk={Math.max(8,caseItem.risk-index)}/></td></tr>})}</tbody></table></div></section>}
  {knowledgeTab==="SIU Decisions"&&<section className="wiki-section knowledge-view"><p className="eyebrow">HUMAN DECISION RECORD</p><h3>Current SIU context</h3><p className="knowledge-intro">System findings support investigator review and do not constitute a final enforcement decision.</p><div className="decision-row"><Badge tone={caseItem.status==="Triage"?"neutral":"info"}>{caseItem.status.toUpperCase()}</Badge><span>Current</span><p>{caseItem.title} · Risk {caseItem.risk}%</p></div>{rules.length>0&&<div className="decision-row"><Badge tone="purple">AI SYNTHESIS</Badge><span>Just now</span><p>{rules.length} findings compiled · Human verification required</p></div>}<div className="decision-row"><Badge tone="success">AUDIT READY</Badge><span>Current</span><p>Evidence provenance and investigator actions are retained.</p></div></section>}</article>
  <aside className="backlink-panel"><p className="eyebrow">BACKLINKS · {backlinkCount}</p><h3>Referenced by</h3>{references.map(reference=><button key={reference.label} onClick={reference.action} title={`Open ${reference.detail.toLowerCase()}`}><span><Icon name="network"/><span><b>{reference.label}</b><small>{reference.detail}</small></span></span><Icon name="chevron"/></button>)}<Button variant="primary" className="full" onClick={()=>setPage("case")}>Open {caseItem.id}</Button></aside></div>
  {searchOpen&&<div className="modal-backdrop" onMouseDown={()=>setSearchOpen(false)}><div className="search-modal knowledge-search-modal" onMouseDown={event=>event.stopPropagation()}><div className="search-modal-input"><Icon name="search"/><input autoFocus value={knowledgeQuery} onChange={event=>setKnowledgeQuery(event.target.value)} placeholder={`Search ${caseItem.id} knowledge…`}/><button className="icon-button" onClick={()=>setSearchOpen(false)}><Icon name="x"/></button></div><div className="knowledge-search-context"><Badge tone="purple">{caseItem.id}</Badge><span>{caseItem.provider} · NPI {caseItem.npi}</span></div><div className="knowledge-search-results">{knowledgeResults.map(entry=><button key={`${entry.tab}-${entry.label}`} onClick={()=>{setKnowledgeTab(entry.tab);setSearchOpen(false);setKnowledgeQuery("")}}><span className="result-icon"><Icon name={entry.tab==="Policy Evidence"?"shield":entry.tab==="Related Claims"?"case":entry.tab==="Network Entities"?"network":"brain"}/></span><span><b>{entry.label}</b><small>{entry.detail}</small></span><Icon name="arrow" size={14}/></button>)}{knowledgeResults.length===0&&<div className="empty-state"><Icon name="search"/><h3>No knowledge found</h3><p>Try a case ID, provider, finding, claim, or policy term.</p></div>}</div></div></div>}</div>;
}

function AuditTrail({caseItem}:{caseItem:QueueCase}) {
  const [ledgerStatus,setLedgerStatus]=useState("VERIFIED LEDGER");
  const [auditQuery,setAuditQuery]=useState("");
  const [actionFilter,setActionFilter]=useState("All actions");
  const [dateFilter,setDateFilter]=useState("Today");
  const [statusFilter,setStatusFilter]=useState("All statuses");
  const [showStatusFilter,setShowStatusFilter]=useState(false);
  const [exportNotice,setExportNotice]=useState("");
  const now=Date.now();
  const auditSeed=Number(caseItem.id.replace(/\D/g,""))||Number(caseItem.npi.slice(-3))||1;
  const eventDefinitions=[
    [caseItem.status==="Referred to SIU"?"SIU Referral Delivered":"Case Status Synchronized",caseItem.status==="Referred to SIU"?"Evidence package sent for human verification":`Current workflow status confirmed as ${caseItem.status}`,"Under Review",caseItem.status],
    ["Provider Intelligence Updated",`Knowledge synthesis refreshed for NPI ${caseItem.npi}`,caseItem.status,caseItem.status],
    ["Evidence Matrix Reviewed",`${caseItem.flag} evidence opened by investigator`,"Open","Under Review"],
    ["Case Opened",`${caseItem.id} selected from the priority queue`,"New","Open"],
  ];
  const events=eventDefinitions.map((event,index)=>({
    timestamp:new Date(now-[2,7,14,28][index]*60_000),
    action:event[0],
    reason:event[1],
    from:event[2],
    to:event[3],
    id:`AUD-${String(auditSeed*100+920-index).padStart(6,"0")}`,
  }));
  const actionOptions=Array.from(new Set(events.map(event=>event.action)));
  const statusOptions=Array.from(new Set(events.map(event=>event.to)));
  const filteredEvents=events.filter(event=>{
    const searchable=`${caseItem.id} ${caseItem.provider} ${caseItem.npi} ${event.action} ${event.reason} ${event.from} ${event.to} Maya Chen ${event.id}`.toLowerCase();
    const matchesQuery=searchable.includes(auditQuery.toLowerCase());
    const matchesAction=actionFilter==="All actions"||event.action===actionFilter;
    const matchesStatus=statusFilter==="All statuses"||event.to===statusFilter;
    const age=now-event.timestamp.getTime();
    const matchesDate=dateFilter==="All time"||(dateFilter==="Today"&&new Date(now).toDateString()===event.timestamp.toDateString())||(dateFilter==="Last 7 days"&&age<=7*86_400_000)||(dateFilter==="Last 30 days"&&age<=30*86_400_000);
    return matchesQuery&&matchesAction&&matchesStatus&&matchesDate;
  });
  const dateFormatter=new Intl.DateTimeFormat("en-US",{month:"short",day:"numeric",year:"numeric"});
  const timeFormatter=new Intl.DateTimeFormat("en-US",{hour:"numeric",minute:"2-digit",second:"2-digit"});
  const exportAudit=()=>{
    if(!filteredEvents.length)return;
    const rows=[
      ["Timestamp","Case ID","Provider","NPI","Action","Reason","Previous Status","Current Status","Investigator","Audit ID"],
      ...filteredEvents.map(event=>[event.timestamp.toISOString(),caseItem.id,caseItem.provider,caseItem.npi,event.action,event.reason,event.from,event.to,"Maya Chen",event.id]),
    ];
    const csv=rows.map(row=>row.map(value=>`"${String(value).replace(/"/g,"\"\"")}"`).join(",")).join("\n");
    const url=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
    const link=document.createElement("a");
    link.href=url;
    link.download=`${caseItem.id.toLowerCase()}-audit-${new Date().toISOString().slice(0,10)}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setExportNotice(`${filteredEvents.length} audit ${filteredEvents.length===1?"event":"events"} exported successfully.`);
    window.setTimeout(()=>setExportNotice(""),3500);
  };
  useEffect(()=>{setLedgerStatus("VERIFIED LEDGER");api.audit(caseItem.id).then(()=>setLedgerStatus("LIVE LEDGER")).catch(()=>undefined)},[caseItem.id]);
  return <div className="page-content"><div className="page-intro"><div><p className="eyebrow">IMMUTABLE EVENT LEDGER</p><h2>Audit Trail</h2><p className="muted">Current investigator and system activity for {caseItem.id} and {caseItem.provider}.</p></div><Button icon="download" onClick={exportAudit} disabled={!filteredEvents.length}>Export audit log</Button></div>{exportNotice&&<div className="audit-export-notice"><Icon name="check"/>{exportNotice}</div>}<Card className="audit-card"><div className="toolbar"><label className="search-input"><Icon name="search"/><input value={auditQuery} onChange={event=>setAuditQuery(event.target.value)} placeholder="Search case, NPI, action, investigator…" aria-label="Search audit events"/>{auditQuery&&<button type="button" onClick={()=>setAuditQuery("")} aria-label="Clear audit search"><Icon name="x" size={13}/></button>}</label><select aria-label="Filter audit actions" value={actionFilter} onChange={event=>setActionFilter(event.target.value)}><option>All actions</option>{actionOptions.map(action=><option key={action}>{action}</option>)}</select><select aria-label="Filter audit dates" value={dateFilter} onChange={event=>setDateFilter(event.target.value)}><option>Today</option><option>Last 7 days</option><option>Last 30 days</option><option>All time</option></select><Button icon="filter" onClick={()=>setShowStatusFilter(!showStatusFilter)}>Filters{statusFilter!=="All statuses"&&<span className="count">1</span>}</Button>{showStatusFilter&&<select aria-label="Filter audit status" value={statusFilter} onChange={event=>setStatusFilter(event.target.value)}><option>All statuses</option>{statusOptions.map(status=><option key={status}>{status}</option>)}</select>}{(auditQuery||actionFilter!=="All actions"||dateFilter!=="Today"||statusFilter!=="All statuses")&&<Button variant="ghost" onClick={()=>{setAuditQuery("");setActionFilter("All actions");setDateFilter("Today");setStatusFilter("All statuses")}}>Clear</Button>}<span className="audit-result-count">{filteredEvents.length} {filteredEvents.length===1?"event":"events"}</span></div><table><thead><tr><th>Timestamp</th><th>Case ID</th><th>Provider / NPI</th><th>Action</th><th>Reason</th><th>Status change</th><th>Investigator</th><th>Audit ID</th></tr></thead><tbody>{filteredEvents.map(event=><tr key={event.id}><td>{dateFormatter.format(event.timestamp)}<small>{timeFormatter.format(event.timestamp)}</small></td><td><b>{caseItem.id}</b></td><td>{caseItem.provider}<small>NPI {caseItem.npi}</small></td><td><Badge tone={event.action.includes("Referral")?"success":event.action.includes("Evidence")?"purple":"info"}>{event.action}</Badge></td><td>{event.reason}</td><td>{event.from} <span className="status-arrow">→</span> {event.to}</td><td>Maya Chen</td><td><button className="audit-id">{event.id}</button></td></tr>)}</tbody></table>{filteredEvents.length===0&&<div className="audit-empty"><Icon name="search" size={25}/><h3>No audit events match</h3><p>Adjust the search, action, date, or status filters to view ledger activity.</p><Button onClick={()=>{setAuditQuery("");setActionFilter("All actions");setDateFilter("Today");setStatusFilter("All statuses")}}>Clear all filters</Button></div>}</Card>
  <Card className="timeline-card"><div className="card-head"><div><p className="eyebrow">{caseItem.id} ACTIVITY</p><h3>Investigation timeline</h3></div><Badge tone="success">{ledgerStatus}</Badge></div><div className="timeline">{events.slice().reverse().map((event,index)=><div className="timeline-event" key={event.id}><span className={`timeline-dot t-${index}`}><Icon name={index===2?"shield":index===3?"brain":"check"} size={14}/></span><time>{timeFormatter.format(event.timestamp)}</time><div><b>{event.action}</b><p>{event.reason}</p><small>Maya Chen · {event.id}</small></div></div>)}</div></Card></div>;
}

function ExecutiveBrief({ setPage }: { setPage:(p:Page)=>void }) {
  const [generating,setGenerating]=useState(false);
  const regenerate=async()=>{setGenerating(true);try{await api.brief("CASE-001")}catch{ /* The evidence-grounded demo brief remains available offline. */ }finally{setGenerating(false)}};
  const sections=[["Executive Summary","CASE-001 presents a high-confidence coordinated fraud pattern involving Dr. Alex Mercer, Apex Diagnostic Lab, and 10 additional entities. The investigation links $842,650 in billed claims to repeat upcoding, duplicate submission, and geographically impossible services."],["Risk Assessment","Composite risk is CRITICAL at 87/100. The score combines a rules result of 91%, ML anomaly score of 82%, and graph centrality in the top 2% of the provider cohort."],["Triggered Rules","CMS-NCCI-2024 §9.3 (upcoding); AHC-FWA-117 §4.2 (geographic integrity); CMS-1500 §24D (duplicate services)."],["ML Findings","CPT 99215 utilization is 4.3× peer median. Billing velocity increased 38% over the last 60 days without a corresponding change in panel size."],["Network Findings","Entity-link analysis identifies a dense 12-entity community connected to Ring East Coast 01, with seven suspicious referral and billing relationships."],["Policy Findings","Sampled documentation does not substantiate high-complexity E/M services. 87% of reviewed claims lack the required decision-making or encounter-time evidence."],["Financial Exposure","$842,650 is currently under investigation. Risk-adjusted projected exposure is $1.64M over 90 days if current billing continues."],["Recommended Investigator Action","Pause payment on the 48 linked claims, request complete medical records, and submit CASE-001 for independent human verification before any further action."]];
  return <div className="page-content brief-page"><div className="case-header"><div><button className="back-link" onClick={()=>setPage("case")}>← Back to CASE-001</button><p className="eyebrow purple-text">AI-GENERATED · EVIDENCE GROUNDED</p><h2>Executive Case Brief</h2><p>CASE-001 · Generated Oct 14, 2026 at 10:48 AM</p></div><div className="case-actions"><Button icon="copy">Copy brief</Button><Button icon="download" onClick={()=>window.print()}>Export PDF</Button><Button variant="primary" icon="refresh" onClick={regenerate} loading={generating}>Regenerate</Button></div></div><div className="brief-layout"><article className="brief-paper"><div className="report-brand"><Brand/><Badge tone="critical">CONFIDENTIAL · SIU</Badge></div>{sections.map((s,i)=><section key={s[0]}><span>{String(i+1).padStart(2,"0")}</span><div><h3>{s[0]}</h3><p>{s[1]}</p></div></section>)}<div className="brief-footer"><Icon name="shield"/> Generated with ClaimShield Nexus AI · Citations verified against policy corpus · Human review required</div></article><aside className="brief-meta"><Card><p className="eyebrow">BRIEF QUALITY</p><div className="quality-score">96<span>%</span></div><p>Evidence coverage</p><div className="quality-row"><span>Policy citations</span><b>3 / 3</b></div><div className="quality-row"><span>Claims referenced</span><b>48</b></div><div className="quality-row"><span>Entity matches</span><b>12</b></div><div className="quality-row"><span>Confidence</span><b>High</b></div></Card><div className="info-note"><Icon name="spark"/><span><b>Responsible AI notice</b>This brief supports investigator review. It does not make a final coverage or enforcement decision.</span></div></aside></div></div>;
}

type SettingsPage = Extract<Page,"personal"|"access"|"regions"|"assignments"|"alerts"|"digest">;

function ToggleRow({ title, detail, defaultOn=true }: { title:string; detail:string; defaultOn?:boolean }) {
  const [enabled,setEnabled]=useState(defaultOn);
  return <div className="toggle-row"><span><b>{title}</b><small>{detail}</small></span><button className={`toggle ${enabled?"on":""}`} onClick={()=>setEnabled(!enabled)} aria-pressed={enabled}><i/></button></div>;
}

function AccountSettings({ page, setPage, onSaved }: { page:SettingsPage; setPage:(page:Page)=>void; onSaved:()=>void }) {
  const config:Record<SettingsPage,{eyebrow:string;title:string;description:string;icon:IconName}> = {
    personal:{eyebrow:"INVESTIGATOR PROFILE",title:"Personal information",description:"Manage your identity and contact details used across SIU workflows.",icon:"provider"},
    access:{eyebrow:"SECURITY & GOVERNANCE",title:"Credentials & access",description:"Review your assigned role, permissions, and professional certifications.",icon:"shield"},
    regions:{eyebrow:"CASE ROUTING",title:"Assigned regions",description:"Manage the markets and investigative queues assigned to your profile.",icon:"network"},
    assignments:{eyebrow:"NOTIFICATION PREFERENCES",title:"Case assignments",description:"Choose how you are notified when investigations enter your queue.",icon:"case"},
    alerts:{eyebrow:"NOTIFICATION PREFERENCES",title:"Critical-risk alerts",description:"Configure immediate alerts for high-exposure claims and fraud rings.",icon:"bell"},
    digest:{eyebrow:"NOTIFICATION PREFERENCES",title:"Daily digest",description:"Schedule a concise summary of queue movement, exposure, and decisions.",icon:"audit"},
  };
  const current=config[page];
  return <div className="page-content settings-page">
    <button className="back-link" onClick={()=>setPage("command")}>← Back to SIU Command Center</button>
    <div className="settings-hero"><span className="settings-hero-icon"><Icon name={current.icon} size={24}/></span><div><p className="eyebrow">{current.eyebrow}</p><h2>{current.title}</h2><p>{current.description}</p></div><Badge tone="success">CHANGES ENCRYPTED</Badge></div>
    <div className="settings-layout"><aside className="settings-nav">
      <p>PROFILE</p>{([["personal","Personal information"],["access","Credentials & access"],["regions","Assigned regions"]] as [SettingsPage,string][]).map(item=><button className={page===item[0]?"active":""} onClick={()=>setPage(item[0])} key={item[0]}>{item[1]}<Icon name="chevron" size={13}/></button>)}
      <p>NOTIFICATIONS</p>{([["assignments","Case assignments"],["alerts","Critical-risk alerts"],["digest","Daily digest"]] as [SettingsPage,string][]).map(item=><button className={page===item[0]?"active":""} onClick={()=>setPage(item[0])} key={item[0]}>{item[1]}<Icon name="chevron" size={13}/></button>)}
    </aside>
    <Card className="settings-card">
      {page==="personal"&&<><div className="settings-card-head"><div><h3>Investigator details</h3><p>Visible to authorized SIU team members and case collaborators.</p></div><div className="settings-avatar">MC</div></div><div className="settings-form"><label><span>First name</span><input defaultValue="Maya"/></label><label><span>Last name</span><input defaultValue="Chen"/></label><label><span>Work email</span><input defaultValue="maya.chen@ahealthcentre.org"/></label><label><span>Investigator ID</span><input defaultValue="SIU-2841" disabled/></label><label><span>Job title</span><input defaultValue="Senior SIU Investigator"/></label><label><span>Direct phone</span><input defaultValue="+1 (212) 555-0184"/></label></div></>}
      {page==="access"&&<><div className="settings-card-head"><div><h3>Access profile</h3><p>Role changes require approval from an SIU administrator.</p></div><Badge tone="success">MFA VERIFIED</Badge></div><div className="access-summary"><div><span>Assigned role</span><b>Senior SIU Investigator</b><small>Enterprise · Northeast Region</small></div><div><span>Last secure sign-in</span><b>Today, 08:42 AM</b><small>New York, NY · Trusted device</small></div></div><p className="settings-label">ACTIVE PERMISSIONS</p><div className="permission-grid">{["Review flagged claims","Pause claim payments","Create SIU referrals","Export case briefs","Access policy vault","View provider networks"].map(item=><span key={item}><Icon name="check" size={14}/>{item}</span>)}</div><p className="settings-label">CERTIFICATIONS</p><div className="certificate"><Icon name="shield"/><span><b>AHFI · Accredited Health Care Fraud Investigator</b><small>Verified · Renewal due May 2027</small></span><Badge tone="success">CURRENT</Badge></div></>}
      {page==="regions"&&<><div className="settings-card-head"><div><h3>Market assignments</h3><p>Cases are routed according to these regional responsibilities.</p></div><Button icon="plus">Request region</Button></div><div className="region-list">{[["Northeast SIU","PRIMARY","New York, New Jersey, Connecticut","284 open cases"],["Mid-Atlantic Support","SUPPORT","Pennsylvania, Delaware","42 shared cases"]].map((region,i)=><div className="region-card" key={region[0]}><span className="region-icon"><Icon name="network"/></span><div><span>{region[1]}</span><h3>{region[0]}</h3><p>{region[2]}</p></div><div><b>{region[3]}</b><small>{i===0?"Full decision authority":"Review and referral access"}</small></div></div>)}</div></>}
      {page==="assignments"&&<><div className="settings-card-head"><div><h3>Assignment notifications</h3><p>Control alerts for changes to your investigation workload.</p></div></div><div className="toggle-list"><ToggleRow title="New case assigned" detail="Notify me when a new investigation enters my queue."/><ToggleRow title="Case reassigned" detail="Notify me when ownership changes on a case I follow."/><ToggleRow title="Medical records received" detail="Notify me when requested evidence becomes available."/><ToggleRow title="Case comment or mention" detail="Notify me when another investigator mentions me."/></div><div className="channel-select"><span>Delivery channels</span><label><input type="checkbox" defaultChecked/> In-app</label><label><input type="checkbox" defaultChecked/> Email</label><label><input type="checkbox"/> SMS</label></div></>}
      {page==="alerts"&&<><div className="settings-card-head"><div><h3>Critical-risk rules</h3><p>These alerts bypass digest delivery and are sent immediately.</p></div><Badge tone="critical">PRIORITY</Badge></div><div className="toggle-list"><ToggleRow title="Composite risk at or above 70%" detail="Critical cases detected by rules, ML, and graph scoring."/><ToggleRow title="Exposure above $500,000" detail="High-dollar cases requiring accelerated review."/><ToggleRow title="New coordinated fraud ring" detail="Graph intelligence identifies a new suspicious community."/><ToggleRow title="Payment deadline within 24 hours" detail="An at-risk claim is approaching adjudication."/></div><div className="threshold-control"><span><b>Custom risk threshold</b><small>Notify when composite risk reaches this level.</small></span><strong>75%</strong><input type="range" min="40" max="95" defaultValue="75"/></div></>}
      {page==="digest"&&<><div className="settings-card-head"><div><h3>Digest schedule</h3><p>Receive one consolidated briefing on your active workload.</p></div><Badge tone="info">NEXT · 7:30 AM</Badge></div><div className="settings-form digest-form"><label><span>Frequency</span><select defaultValue="Weekdays"><option>Every day</option><option>Weekdays</option><option>Weekly</option></select></label><label><span>Delivery time</span><input type="time" defaultValue="07:30"/></label><label><span>Time zone</span><select><option>Eastern Time (ET)</option><option>Central Time (CT)</option><option>Pacific Time (PT)</option></select></label><label><span>Delivery method</span><select><option>Email and in-app</option><option>In-app only</option><option>Email only</option></select></label></div><p className="settings-label">INCLUDE IN DIGEST</p><div className="toggle-list compact"><ToggleRow title="Priority queue movement" detail="New, escalated, and reassigned investigations."/><ToggleRow title="Financial exposure summary" detail="30/60/90-day projected loss changes."/><ToggleRow title="AI and policy findings" detail="New Copilot insights and policy matches."/></div></>}
      <div className="settings-actions"><span><Icon name="shield"/> Changes are written to your security audit log.</span><div><Button onClick={()=>setPage("command")}>Cancel</Button><Button variant="primary" icon="check" onClick={onSaved}>Save changes</Button></div></div>
    </Card></div>
  </div>;
}

function SearchModal({ onClose, openCase, setPage }: { onClose:()=>void; openCase:()=>void; setPage:(p:Page)=>void }) {
  const [q,setQ]=useState(""); const loading=false;
  return <div className="modal-backdrop" onMouseDown={onClose}><div className="search-modal" onMouseDown={e=>e.stopPropagation()}><div className="search-modal-input"><Icon name="search"/><input autoFocus value={q} onChange={e=>setQ(e.target.value)} placeholder="Search cases, providers, claims, fraud rings…"/><kbd>ESC</kbd></div>{loading?<div className="skeleton-search"><i/><i/><i/></div>:<div className="search-results"><div className="recent-head"><span>{q?"TOP RESULTS":"RECENT SEARCHES"}</span><button>Clear</button></div>{!q&&["CASE-001","Dr. Alex Mercer","Ring East Coast 01"].map(x=><button className="recent-item" onClick={()=>setQ(x)} key={x}><Icon name="clock"/>{x}<Icon name="arrow"/></button>)}{q&&<><p className="result-group">CASES</p><button className="search-result selected" onClick={openCase}><span className="result-icon"><Icon name="case"/></span><span><b>CASE-001</b><small>High-Dollar Coordinated Fraud Ring</small></span><RiskBadge risk={87}/></button><p className="result-group">PROVIDERS</p><button className="search-result" onClick={()=>{setPage("provider");onClose()}}><span className="result-icon"><Icon name="provider"/></span><span><b>Dr. Alex Mercer</b><small>NPI 1029384 · Internal Medicine</small></span><Badge tone="critical">HIGH RISK</Badge></button><p className="result-group">FRAUD RINGS</p><button className="search-result" onClick={openCase}><span className="result-icon"><Icon name="network"/></span><span><b>Ring East Coast 01</b><small>12 entities · $3.2M exposure</small></span><Icon name="chevron"/></button></>}</div>}<div className="search-footer"><span><kbd>↑↓</kbd> Navigate</span><span><kbd>↵</kbd> Open</span><span><kbd>ESC</kbd> Close</span></div></div></div>;
}

function ActionDialog({ action, caseItem, connected, onClose, onSuccess }: { action:string; caseItem:QueueCase; connected:boolean; onClose:()=>void; onSuccess:()=>void }) {
  const [reason,setReason]=useState(""); const [state,setState]=useState<"default"|"processing"|"success"|"error">("default");
  const confirm=async()=>{setState("processing");
    
const actionMap: Partial<Record<string, InvestigatorAction>> = {
  "Approve": "APPROVE_SIU",
  "Request Medical Records": "REQUEST_INFO",
  "Mark False Positive": "DISMISS",
};

  if(!connected){window.setTimeout(()=>setState("success"),700);return}const apiAction=actionMap[action];if(!apiAction){setState("error");return}try{await api.action(caseItem.id,apiAction,reason);setState("success")}catch{setState("error")}};
  if(state==="success") return <div className="modal-backdrop"><div className="dialog success-dialog"><div className="success-icon"><Icon name="check" size={28}/></div>
  <h2>{connected?`${action} recorded`:"Demo action prepared"}</h2><p>{connected?`${caseItem.id} action was recorded in the backend audit ledger.`:"Demo mode is offline; no backend action was submitted."}</p><Button variant="primary" onClick={()=>{onSuccess();onClose()}} className="full">View case</Button></div></div>;
  return <div className="modal-backdrop"><div className="dialog"><div className="dialog-head"><span className={`dialog-icon ${action.includes("Pause")?"danger":""}`}><Icon name="shield"/></span><div><p className="eyebrow">INVESTIGATOR ACTION</p><h2>{action} for {caseItem.id}?</h2></div><button className="icon-button" onClick={onClose}><Icon name="x"/></button></div><div className="dialog-case"><span><b>{caseItem.id}</b><small>{caseItem.title}</small></span><RiskBadge risk={caseItem.risk}/></div><label className="full-field"><span>Action reason <b>*</b></span><textarea value={reason} onChange={e=>setReason(e.target.value)} placeholder="Document evidence and rationale for this action…"/></label><div className="compliance-note"><Icon name="audit"/><span>{action==="Refer to SIU"?"SIU referral delivery is not supported by the current backend API.":"This action will be added to the immutable audit trail with your investigator ID and timestamp."}</span></div>{state==="error"&&<div className="error-note">{action==="Pause Payment"?"Payment holds are not supported by the current backend API. No payment action was recorded.":action==="Refer to SIU"?"SIU referrals are not supported by the current backend API. No referral was sent.":"Unable to complete this action. Check your connection and retry."}</div>}<div className="dialog-actions"><Button onClick={onClose}>Cancel</Button><Button variant={action.includes("Pause")?"danger":"primary"} onClick={confirm} disabled={!reason.trim()} loading={state==="processing"}>Confirm {action}</Button></div></div></div>;
}

function Copilot({ onClose, onBrief, caseItem }: { onClose:()=>void; onBrief:()=>void; caseItem:QueueCase }) {
  type CopilotMode="welcome"|"policy"|"guardrail"|"network"|"provider"|"loading";
  const [mode,setMode]=useState<CopilotMode>("welcome");
  const rules=getTriggeredRules(caseItem);
  const claimCount=caseItem.risk<40?6:48;
  const entityCount=Math.max(2,Math.round(caseItem.risk/7));
  const questions:Record<Exclude<CopilotMode,"welcome"|"loading">,string>={
    policy:`Which policy rules apply to ${caseItem.id}?`,
    guardrail:"Can you diagnose what condition this patient actually has?",
    network:`Explain the fraud network connected to ${caseItem.id}.`,
    provider:`Summarize the risk for ${caseItem.provider}.`,
  };
  useEffect(()=>{api.copilotContext(caseItem.id).catch(()=>undefined);setMode("welcome")},[caseItem.id]);
  const ask=async(next:Exclude<CopilotMode,"welcome"|"loading">)=>{setMode("loading");try{await api.chat(caseItem.id,questions[next])}catch{ /* Preserve the safe, evidence-grounded demo response offline. */ }finally{setMode(next)}};
  return <div className="drawer-backdrop" onMouseDown={onClose}><aside className="copilot" onMouseDown={e=>e.stopPropagation()}><div className="copilot-head"><div className="copilot-title"><span><Icon name="spark"/></span><div><h2>AI Investigation Copilot</h2><p><i/> Context Ready · {caseItem.id}</p></div></div><div><button className="icon-button" title="Clear chat" onClick={()=>setMode("welcome")}><Icon name="refresh"/></button><button className="icon-button" onClick={onClose}><Icon name="x"/></button></div></div><div className="context-bar"><span>{caseItem.id}</span><span>{claimCount} claims</span><span>{rules.length} policies</span><span>{entityCount} entities</span></div>
  <div className="chat"><div className="ai-message"><span className="ai-avatar"><Icon name="spark"/></span><div><b>ClaimShield Copilot</b><p>I’m grounded in the evidence for {caseItem.id}. I can explain policy findings, network relationships, and billing patterns for {caseItem.provider}.</p></div></div>
  {mode!=="welcome"&&mode!=="loading"&&<div className="user-message"><p>{questions[mode]}</p><span>MC</span></div>}
  {mode==="loading"&&<div className="ai-message"><span className="ai-avatar"><Icon name="spark"/></span><div className="typing"><i/><i/><i/></div></div>}
  {mode==="policy"&&<div className="ai-message"><span className="ai-avatar"><Icon name="spark"/></span><div><b>ClaimShield Copilot</b><p><strong>{rules.length?`${rules.length} policy-linked findings require review.`:"No material policy conflict is currently supported."}</strong> The primary case finding is {caseItem.flag.toLowerCase()}.</p>{rules.length>0&&<><div className="evidence-quote"><label>CASE EVIDENCE</label><p>{rules.map(rule=>rule[0]).join(", ")} were identified in the evidence matrix for {caseItem.provider}.</p><small>Source: {caseItem.id} · Explainable Evidence Matrix</small></div><div className="evidence-quote policy"><label>POLICY CONTEXT</label><p>Each finding is mapped to the validated policy index. Human interpretation is required before adverse action.</p><small>Risk {caseItem.risk}% · NPI {caseItem.npi}</small></div></>}</div></div>}
  {mode==="guardrail"&&<div className="ai-message"><span className="ai-avatar"><Icon name="shield"/></span><div><b>ClaimShield Copilot</b><p><strong>I can’t diagnose a patient’s medical condition.</strong> I can help analyze the claim, billing patterns, applicable policy rules, and fraud/waste/abuse indicators.</p><label className="alternative-label">I CAN HELP WITH</label><div className="alternative-actions"><button onClick={()=>ask("provider")}>Analyze Billing Behavior</button><button onClick={()=>ask("policy")}>Explain Policy Violation</button><button onClick={()=>ask("network")}>Summarize FWA Indicators</button></div></div></div>}
  {mode==="network"&&<div className="ai-message"><span className="ai-avatar"><Icon name="network"/></span><div><b>ClaimShield Copilot</b><p><strong>{entityCount} entities are connected to {caseItem.id}.</strong> The network is associated with {caseItem.flag.toLowerCase()} and {claimCount} linked claims.</p><div className="evidence-quote"><label>NETWORK INTERPRETATION</label><p>{caseItem.risk>=70?"The concentration is materially above the expected peer baseline and warrants human network review.":"Connections are present but do not independently establish coordinated fraud."}</p><small>{caseItem.provider} · NPI {caseItem.npi}</small></div></div></div>}
  {mode==="provider"&&<div className="ai-message"><span className="ai-avatar"><Icon name="provider"/></span><div><b>ClaimShield Copilot</b><p><strong>{caseItem.provider} has a composite risk score of {caseItem.risk}%.</strong> The current case exposure is {caseItem.billed}, with {rules.length} active {rules.length===1?"finding":"findings"}.</p><div className="evidence-quote"><label>PROVIDER SUMMARY</label><p>Primary finding: {caseItem.flag}. Current workflow status: {caseItem.status}. Human verification remains required for final action.</p><small>{caseItem.id} · NPI {caseItem.npi}</small></div></div></div>}
  </div><div className="prompt-area"><div className="prompt-chips"><button onClick={()=>ask("policy")}>Check Policy Compliance</button><button onClick={()=>ask("guardrail")}>Test Safety Guardrail</button><button onClick={onBrief}>Draft Executive Case Brief</button><button onClick={()=>ask("network")}>Explain Fraud Network</button><button onClick={()=>ask("provider")}>Summarize Provider Risk</button></div><div className="prompt-input"><textarea placeholder={`Ask about ${caseItem.id} evidence…`} defaultValue={mode==="welcome"?`Summarize the evidence for ${caseItem.id}.`:""}/><button onClick={()=>ask("provider")}><Icon name="arrow"/></button></div><p>AI can make mistakes. Verify evidence before taking action.</p></div></aside></div>;
}

export default function App() {
  const [authenticated,setAuthenticated]=useState(false);
  const [page,setPage]=useState<Page>("command");
  const [collapsed,setCollapsed]=useState(false);
  const [search,setSearch]=useState(false);
  const [copilot,setCopilot]=useState(false);
  const [action,setAction]=useState<string|null>(null);
  const [toast,setToast]=useState("");
  const [queueCases,setQueueCases]=useState<QueueCase[]>(demoCases);
  const [selectedCase,setSelectedCase]=useState<QueueCase>(demoCases[0]);
  const [connected,setConnected]=useState(false);
  useEffect(()=>{Promise.all([api.health(),api.queue()]).then(([,queue])=>{
    if(queue.length){
      const liveIds=new Set(queue.map(item=>item.id));
      const supplemented=[...queue,...demoCases.filter(item=>!liveIds.has(item.id))];
      setQueueCases(supplemented.length>=12?supplemented:demoCases);
    }
    setConnected(true);
  }).catch(()=>setConnected(false))},[]);
  const titles:Record<Page,string>={command:"SIU Command Center",case:"Case Investigation",provider:"Provider Intelligence",analyzer:"Real-Time Claim Analyzer",brain:"Deep-Dive Workspace",audit:"Audit Trail",brief:"Executive Case Brief",personal:"Personal Information",access:"Credentials & Access",regions:"Assigned Regions",assignments:"Case Assignment Notifications",alerts:"Critical-Risk Alerts",digest:"Daily Digest"};
  const openCase=(caseItem:QueueCase=selectedCase)=>{setSelectedCase(caseItem);setPage("case");setSearch(false)};
  const content=useMemo(()=>{
    if(page==="command") return <CommandCenter openCase={openCase} openAction={setAction} cases={queueCases} selectedCase={selectedCase} onSelectCase={setSelectedCase}/>;
    if(page==="case") return <CaseWorkspace setPage={setPage} openAction={setAction} onCopilot={()=>setCopilot(true)} caseItem={selectedCase}/>;
    if(page==="provider") return <ProviderPage setPage={setPage} caseItem={selectedCase}/>;
    if(page==="analyzer") return <SandboxView><ClaimAnalyzer caseItem={selectedCase}/></SandboxView>;
    if(page==="brain") return <SecondBrain setPage={setPage} caseItem={selectedCase} onCopilot={()=>setCopilot(true)}/>;
    if(page==="audit") return <AuditTrail caseItem={selectedCase}/>;
    if(page==="brief") return <ExecutiveBrief setPage={setPage}/>;
    return <AccountSettings page={page} setPage={setPage} onSaved={()=>{setToast("Your profile preferences were saved to the secure audit log.");setTimeout(()=>setToast(""),3500)}}/>;
  },[page,queueCases,selectedCase]);
  if(!authenticated) return <Login onLogin={()=>setAuthenticated(true)}/>;
  return <div className="app-shell"><Sidebar page={page} setPage={setPage} collapsed={collapsed} onCollapse={()=>setCollapsed(!collapsed)}/><div className="app-main"><Header title={titles[page]} onSearch={()=>setSearch(true)} onSignOut={()=>setAuthenticated(false)} onNavigate={setPage} connected={connected}/>{content}</div>
    {search&&<SearchModal onClose={()=>setSearch(false)} openCase={openCase} setPage={setPage}/>}
    {copilot&&<Copilot caseItem={selectedCase} onClose={()=>setCopilot(false)} onBrief={()=>{setCopilot(false);setPage("brief")}}/>}
    {action&&<ActionDialog action={action} caseItem={selectedCase} connected={connected} onClose={()=>setAction(null)} onSuccess={()=>{
      if(action==="Refer to SIU"){
        const referredCase={...selectedCase,status:"Referred to SIU",updated:"Just now"};
        setSelectedCase(referredCase);
        setQueueCases(current=>current.map(item=>item.id===referredCase.id?referredCase:item));
        setToast(`SIU referral delivered for ${selectedCase.id}. The case is now awaiting human verification.`);
      }else{
        setToast(`Compiling action into Institutional Knowledge Vault (NPI-${selectedCase.npi}.md)...`);
      }
      setTimeout(()=>setToast(""),4500);
    }}/>}
    {toast&&<div className="toast"><span><Icon name={toast.startsWith("SIU referral")?"shield":"spark"}/></span><div><b>{toast.startsWith("SIU referral")?"SIU referral delivered":"Institutional memory updated"}</b><p>{toast.startsWith("SIU referral")?toast:`⚡ ${toast}`}</p></div><button onClick={()=>setToast("")}><Icon name="x"/></button></div>}
  </div>;
}
