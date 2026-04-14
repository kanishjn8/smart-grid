const NODE_POSITIONS = {
  N1: { x: 160, y: 110, label: "Solar" },
  N2: { x: 840, y: 110, label: "Wind" },
  N3: { x: 500, y: 180, label: "Storage" },
  N4: { x: 840, y: 310, label: "Consumer" },
  N5: { x: 500, y: 300, label: "Microgrid" },
  N6: { x: 300, y: 470, label: "EV" },
  N7: { x: 700, y: 470, label: "Battery" },
  N8: { x: 500, y: 555, label: "Backup" },
};

const EDGES = [
  ["N1", "N3"],
  ["N2", "N3"],
  ["N3", "N5"],
  ["N4", "N5"],
  ["N5", "N6"],
  ["N5", "N7"],
  ["N6", "N8"],
  ["N7", "N8"],
  ["N3", "N8"],
];

const stateUrl = "/api/state";
const edgeLayer = document.querySelector("#edge-layer");
const nodeLayer = document.querySelector("#node-layer");
const nodeGrid = document.querySelector("#node-grid");
const gossipLog = document.querySelector("#gossip-log");
const eventLog = document.querySelector("#event-log");
const pauseBtn = document.querySelector("#pause-btn");
const faultBtn = document.querySelector("#fault-btn");
const resetBtn = document.querySelector("#reset-btn");

const metricTick = document.querySelector("#metric-tick");
const metricElapsed = document.querySelector("#metric-elapsed");
const metricLeader = document.querySelector("#metric-leader");
const metricStatus = document.querySelector("#metric-status");
const metricStatusChip = document.querySelector("#metric-status-chip");
const metricBalance = document.querySelector("#metric-balance");
const metricConvergence = document.querySelector("#metric-convergence");
const metricSummary = document.querySelector("#metric-summary");
const pausedPill = document.querySelector("#paused-pill");
const balanceFill = document.querySelector("#balance-fill");

let fetching = false;
let edgeElements = new Map();
let pointElements = new Map();

function initScene() {
  EDGES.forEach(([from, to]) => {
    const start = NODE_POSITIONS[from];
    const end = NODE_POSITIONS[to];
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", start.x);
    line.setAttribute("y1", start.y);
    line.setAttribute("x2", end.x);
    line.setAttribute("y2", end.y);
    line.setAttribute("class", "edge");
    edgeLayer.appendChild(line);
    edgeElements.set(`${from}-${to}`, line);
  });

  Object.entries(NODE_POSITIONS).forEach(([nodeId, position]) => {
    const el = document.createElement("article");
    el.className = "node-point";
    el.style.left = `${(position.x / 1000) * 100}%`;
    el.style.top = `${(position.y / 620) * 100}%`;
    el.dataset.nodeId = nodeId;
    nodeLayer.appendChild(el);
    pointElements.set(nodeId, el);
  });
}

function classForStatus(node) {
  if (!node.alive || node.status === "CRASHED") return "crashed";
  if (node.in_critical_section || node.status === "MUTEX") return "mutex";
  if (node.requesting_mutex || node.status === "REQUESTING") return "requesting";
  if (node.replicating) return "replicating";
  if (node.is_leader) return "leader";
  return "";
}

function powerText(value) {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}kW`;
}

function renderPoint(node) {
  const element = pointElements.get(node.node_id);
  const statusClass = classForStatus(node);
  element.className = `node-point ${statusClass} ${node.is_leader ? "leader" : ""}`.trim();
  element.innerHTML = `
    <strong>${node.node_id} ${node.is_leader ? "★" : ""}</strong>
    <div>${node.node_type}</div>
    <div class="power">${powerText(node.power_output)}</div>
    <div class="meta">
      <span>[${String(node.lamport_clock).padStart(3, "0")}]</span>
      <span>${node.status}</span>
    </div>
  `;
}

function renderNodeGrid(nodes) {
  nodeGrid.innerHTML = nodes
    .map((node) => {
      const statusClass = classForStatus(node);
      return `
        <article class="node-card ${statusClass} ${node.is_leader ? "leader" : ""}">
          <div class="panel-header">
            <div>
              <p class="label">${node.node_id}</p>
              <strong>${node.node_type}${node.is_leader ? " ★" : ""}</strong>
            </div>
            <span class="status-tag">${node.status}</span>
          </div>
          <div class="power">${powerText(node.power_output)}</div>
          <div class="meta">
            <span>Lamport [${String(node.lamport_clock).padStart(3, "0")}]</span>
            <span>${node.known_state_size} known</span>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderLogs(container, entries, typeKey) {
  if (!entries.length) {
    container.innerHTML = `<div class="empty-state">Waiting for ${typeKey} activity...</div>`;
    return;
  }
  container.innerHTML = entries
    .slice()
    .reverse()
    .map((entry) => {
      const styleKey = String(entry[typeKey]).toLowerCase();
      return `<div class="log-entry ${styleKey}">${entry.text}</div>`;
    })
    .join("");
}

function statusTheme(status) {
  if (status === "CRITICAL") return { className: "critical", color: "var(--critical)" };
  if (status === "STRESSED") return { className: "stressed", color: "var(--stressed)" };
  return { className: "stable", color: "var(--stable)" };
}

function updateEdges(nodes, messages) {
  const nodeMap = Object.fromEntries(nodes.map((node) => [node.node_id, node]));
  const recent = new Map();

  messages.slice(-8).forEach((message) => {
    const key = [message.sender, message.receiver].sort().join("-");
    recent.set(key, message.type);
  });

  edgeElements.forEach((line, key) => {
    const [from, to] = key.split("-");
    const fromNode = nodeMap[from];
    const toNode = nodeMap[to];
    const recentType = recent.get(key);
    const mutexOnEdge =
      [fromNode, toNode].some((node) => node.in_critical_section || node.requesting_mutex) &&
      recentType !== "GOSSIP";

    let className = "edge";
    if (!fromNode.alive || !toNode.alive) {
      className += " edge--crashed";
    } else if (recentType === "REPLICATE") {
      className += " edge--replicate";
    } else if (recentType === "GOSSIP" || recentType === "ELECTION" || recentType === "COORDINATOR") {
      className += " edge--gossip";
    } else if (mutexOnEdge || recentType === "REQUEST" || recentType === "REPLY") {
      className += " edge--mutex";
    }
    line.setAttribute("class", className);
  });
}

function updateMetrics(snapshot) {
  metricTick.textContent = String(snapshot.tick).padStart(3, "0");
  metricElapsed.textContent = `${snapshot.elapsed.toFixed(1)}s`;
  metricLeader.textContent = snapshot.leader || "None";
  metricStatus.textContent = snapshot.status;
  metricBalance.textContent = powerText(snapshot.balance);
  metricConvergence.textContent = snapshot.convergence;

  const theme = statusTheme(snapshot.status);
  metricStatusChip.className = `metric-chip metric-status ${theme.className}`;

  const percent = Math.min(Math.abs(snapshot.balance) / 4.5, 1) * 100;
  balanceFill.style.width = `${percent}%`;
  balanceFill.style.background =
    snapshot.status === "CRITICAL"
      ? "linear-gradient(90deg, var(--critical), #ff8b79)"
      : snapshot.status === "STRESSED"
        ? "linear-gradient(90deg, var(--stressed), #ffe299)"
        : "linear-gradient(90deg, var(--stable), #92ffc2)";

  pausedPill.textContent = snapshot.paused ? "Paused" : "Live";
  pauseBtn.textContent = snapshot.paused ? "Resume" : "Pause";
  metricSummary.textContent =
    snapshot.status === "CRITICAL"
      ? "The grid is leaning on backup capacity and distributed coordination is under pressure."
      : snapshot.status === "STRESSED"
        ? "The grid is absorbing a disturbance while gossip and mutex coordination rebalance the load."
        : "Power supply and demand are within tolerance and gossip convergence is stabilizing the fleet.";
}

function renderSnapshot(snapshot) {
  updateMetrics(snapshot);
  snapshot.nodes.forEach(renderPoint);
  renderNodeGrid(snapshot.nodes);
  renderLogs(gossipLog, snapshot.messages, "type");
  renderLogs(eventLog, snapshot.events, "type");
  updateEdges(snapshot.nodes, snapshot.messages);
}

async function fetchState() {
  if (fetching) return;
  fetching = true;
  try {
    const response = await fetch(stateUrl, { cache: "no-store" });
    const snapshot = await response.json();
    renderSnapshot(snapshot);
  } catch (error) {
    metricSummary.textContent = `Frontend lost contact with the local API: ${error}`;
  } finally {
    fetching = false;
  }
}

async function postControl(path) {
  await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  await fetchState();
}

pauseBtn.addEventListener("click", () => postControl("/api/control/pause"));
faultBtn.addEventListener("click", () => postControl("/api/control/fault"));
resetBtn.addEventListener("click", () => postControl("/api/control/reset"));

initScene();
fetchState();
setInterval(fetchState, 500);
